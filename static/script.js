// Global variables
let currentTargetTemp;
let currentSetTemp;
let currentMode;
let currentTargetMode;
let userNotRequestingChange = true;
let userNotRequestingChangeMode = true;
let autoUpdatePaused = false;
let timeout = 10000;
let currentVersion = null;

// Helper function to show feedback messages
function showFeedback(message, isError = false, isWarning = false) {
    const feedback = document.getElementById('feedback');
    feedback.textContent = message;
    feedback.classList.remove('error', 'warning');
    
    if (isError) {
        feedback.classList.add('error');
    } else if (isWarning) {
        feedback.classList.add('warning');
    }
    
    feedback.style.display = 'block';
    setTimeout(() => {
        feedback.style.display = 'none';
    }, 3000);
}

// Utility function to fetch with a timeout
function fetchWithTimeout(url, options, timeout = 5000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    return fetch(url, {
        ...options,
        signal: controller.signal
    }).finally(() => clearTimeout(id));
}

// Function to check server readiness
function checkServerHealth() {
    fetchWithTimeout("http://blade:5000/health", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        initializeDesiredTemperature();
    })
    .catch(error => {
        console.error('Server health check failed, retrying:', error);
        setTimeout(checkServerHealth, 2000);
    });
}

// Function to initialize the desired temperature
function initializeDesiredTemperature() {
    // First fetch the current mode
    fetchWithTimeout("http://blade:5000/current_mode", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(modeData => {
        currentMode = modeData.current_mode.toLowerCase();
        currentTargetMode = currentMode;
        document.getElementById("current-mode").innerText = currentMode.toUpperCase();
        updateModeButtons(currentMode);
        
        // Then fetch the temperature
        return fetchWithTimeout("http://blade:5000/set_temperature", {
            method: 'GET',
            mode: 'cors',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        }, timeout);
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        currentSetTemp = data.desired_temperature;
        currentTargetTemp = currentSetTemp;
        
        // Update temperature displays based on mode
        if (currentMode && currentMode.toLowerCase() === 'off') {
            document.getElementById("set-temperature").innerText = "OFF";
            document.getElementById("desired-temperature").innerText = 'OFF';
        } else {
            document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
            document.getElementById("desired-temperature").innerText = currentSetTemp;
        }
    })
    .catch(error => reloadPageIfNeeded(error));
}

// Function to update mode buttons
function updateModeButtons(mode) {
    document.querySelectorAll('.btn-mode').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.querySelector(`.btn-mode[data-mode="${mode.toLowerCase()}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Update control card class for mode-specific styling
    const controlCard = document.querySelector('.control-card');
    if (controlCard) {
        controlCard.classList.remove('mode-off', 'mode-heat', 'mode-cool');
        controlCard.classList.add(`mode-${mode.toLowerCase()}`);
    }
    
    // Hide/show temperature based on mode
    const tempDisplay = document.getElementById('desired-temperature');
    const setTempDisplay = document.getElementById('set-temperature');
    if (mode.toLowerCase() === 'off') {
        tempDisplay.innerText = 'OFF';
        if (setTempDisplay) {
            setTempDisplay.innerText = 'OFF';
        }
    } else {
        tempDisplay.innerText = currentTargetTemp || currentSetTemp || '--';
    }
}

// Function to set mode
function setMode(mode) {
    currentTargetMode = mode;
    userNotRequestingChangeMode = false;
    autoUpdatePaused = true;
    
    fetchWithTimeout("http://blade:5000/set_mode", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify({ mode: mode })
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        currentMode = mode;
        document.getElementById("current-mode").innerText = mode.toUpperCase();
        updateModeButtons(mode);
        userNotRequestingChangeMode = true;
        autoUpdatePaused = false;
        showFeedback(`Mode set to ${mode.toUpperCase()}`);
    })
    .catch(error => {
        console.error('Error setting mode:', error);
        showFeedback("Failed to set mode", true);
        autoUpdatePaused = false;
    });
}

// Function to adjust temperature
function adjustTemperature(change) {
    // Don't allow temperature adjustment in OFF mode
    if (currentMode && currentMode.toLowerCase() === 'off') {
        showFeedback("Cannot adjust temperature in OFF mode", false, true);
        return;
    }
    
    currentTargetTemp += change;
    if (currentTargetTemp < 50) currentTargetTemp = 50;
    if (currentTargetTemp > 90) currentTargetTemp = 90;
    
    document.getElementById("desired-temperature").innerText = currentTargetTemp;
    userNotRequestingChange = false;
    autoUpdatePaused = true;
    
    // Send update after a short delay
    clearTimeout(window.tempUpdateTimer);
    window.tempUpdateTimer = setTimeout(sendTemperatureUpdate, 500);
}

// Function to send temperature update
function sendTemperatureUpdate() {
    if (currentTargetTemp !== currentSetTemp) {
        console.log('Sending temperature update:', currentTargetTemp);
        fetchWithTimeout("http://blade:5000/set_temperature", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ temperature: currentTargetTemp })
        }, timeout)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            userNotRequestingChange = true;
            autoUpdatePaused = false;
            showFeedback("Temperature updated successfully");
        })
        .catch(error => {
            console.error('Error sending temperature update:', error);
            showFeedback("Failed to update temperature", true);
            autoUpdatePaused = false;
        });
    }
}

// Function to activate light
function activateLight() {
    const lightBtn = document.getElementById('light-btn');
    lightBtn.classList.add('active');
    
    fetchWithTimeout("http://blade:5000/activate_light", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showFeedback('Light activated successfully');
        setTimeout(() => {
            lightBtn.classList.remove('active');
        }, 3000);
    })
    .catch(error => {
        console.error('Error activating light:', error);
        showFeedback('Failed to activate light', true);
        lightBtn.classList.remove('active');
    });
}

// Function to update all status values
function updateStatus() {
    if (autoUpdatePaused) return;
    
    // Update time since last action
    fetchWithTimeout("http://blade:5000/time_since_last_action", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(data => {
        document.getElementById("time-since-last-action").innerText = data.time_since_last_action + "s ago";
    })
    .catch(error => console.error('Error fetching time since last action:', error));
    
    // Update desired temperature
    fetchWithTimeout("http://blade:5000/set_temperature", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(data => {
        currentSetTemp = data.desired_temperature;
        
        // Update temperature displays based on mode
        if (currentMode && currentMode.toLowerCase() === 'off') {
            document.getElementById("set-temperature").innerText = "OFF";
            document.getElementById("desired-temperature").innerText = 'OFF';
        } else {
            document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
            if (currentSetTemp !== currentTargetTemp && userNotRequestingChange) {
                currentTargetTemp = currentSetTemp;
                document.getElementById("desired-temperature").innerText = currentSetTemp;
            }
        }
    })
    .catch(error => console.error('Error fetching desired temperature:', error));
    
    // Update current mode
    fetchWithTimeout("http://blade:5000/current_mode", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(data => {
        currentMode = data.current_mode.toLowerCase();
        if (currentTargetMode == null) {
            currentTargetMode = currentMode;
        }
        if (currentMode !== currentTargetMode && userNotRequestingChangeMode) {
            document.getElementById("current-mode").innerText = currentMode.toUpperCase();
            updateModeButtons(currentMode);
            currentTargetMode = currentMode;
        }
    })
    .catch(error => console.error('Error fetching current mode:', error));
    
    // Update temperature settings
    fetchWithTimeout("http://blade:5000/temperature_settings", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(data => {
        document.getElementById("heat-temperature").innerText = data.current_heat_temp + "°F";
        document.getElementById("cool-temperature").innerText = data.current_cool_temp + "°F";
    })
    .catch(error => console.error('Error fetching temperature settings:', error));
}

// Function to format datetime
function formatDateTime(dateStr) {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Function to display scheduled items
function displayScheduledItems() {
    fetchWithTimeout("http://blade:5000/get_scheduled_events", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(schedules => {
        const container = document.getElementById('scheduled-items');
        container.innerHTML = '';
        
        if (schedules.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #6c757d;">No schedules configured</p>';
            return;
        }
        
        schedules.forEach(item => {
            const scheduleDiv = document.createElement('div');
            scheduleDiv.classList.add('schedule-item');
            
            const infoDiv = document.createElement('div');
            infoDiv.classList.add('schedule-info');
            
            const mainInfo = document.createElement('div');
            // Don't show temperature for OFF mode
            const tempDisplay = item.mode.toLowerCase() === 'off' ? '' : `${item.temperature}°F `;
            mainInfo.innerHTML = `<strong>${item.time}</strong> - ${tempDisplay}${item.mode.toUpperCase()} - ${item.days_of_week}`;
            infoDiv.appendChild(mainInfo);
            
            // Add metadata if available
            if (item.next_execution || item.last_error) {
                const metaDiv = document.createElement('div');
                metaDiv.classList.add('schedule-meta');
                
                if (item.next_execution) {
                    metaDiv.innerHTML += `Next: ${formatDateTime(item.next_execution)}`;
                }
                if (item.last_error) {
                    metaDiv.innerHTML += ` <span style="color: #dc3545;">⚠ ${item.last_error}</span>`;
                }
                
                infoDiv.appendChild(metaDiv);
            }
            
            const actionsDiv = document.createElement('div');
            actionsDiv.classList.add('schedule-actions');
            
            const toggleBtn = document.createElement('button');
            toggleBtn.classList.add('btn-toggle', item.enabled ? 'enabled' : 'disabled');
            toggleBtn.textContent = item.enabled ? 'Enabled' : 'Disabled';
            toggleBtn.onclick = () => toggleSchedule(item.id, !item.enabled);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('btn-delete');
            deleteBtn.textContent = 'Delete';
            deleteBtn.onclick = () => deleteScheduledItem(item.id);
            
            actionsDiv.appendChild(toggleBtn);
            actionsDiv.appendChild(deleteBtn);
            
            scheduleDiv.appendChild(infoDiv);
            scheduleDiv.appendChild(actionsDiv);
            container.appendChild(scheduleDiv);
        });
    })
    .catch(error => console.error('Error fetching scheduled events:', error));
}

// Function to toggle schedule
function toggleSchedule(id, enabled) {
    fetchWithTimeout(`http://blade:5000/update_schedule/${id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify({ enabled: enabled })
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showFeedback('Schedule updated successfully');
        displayScheduledItems();
    })
    .catch(error => {
        console.error('Error updating schedule:', error);
        showFeedback('Failed to update schedule', true);
    });
}

// Function to delete scheduled item
function deleteScheduledItem(id) {
    if (!confirm('Are you sure you want to delete this schedule?')) {
        return;
    }
    
    fetchWithTimeout(`http://blade:5000/delete_schedule/${id}`, {
        method: "DELETE",
        headers: {
            "Accept": "application/json"
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showFeedback('Schedule deleted successfully');
        displayScheduledItems();
    })
    .catch(error => {
        console.error('Error deleting schedule:', error);
        showFeedback('Failed to delete schedule', true);
    });
}

// Function to submit schedule
function submitSchedule() {
    const time = document.getElementById('schedule-time').value;
    const tempInput = document.getElementById('schedule-temp');
    const temp = tempInput.value;
    const mode = document.getElementById('schedule-mode').value;
    const days = document.getElementById('schedule-days').value;
    
    // For OFF mode, temperature is not required
    if (!time || !mode) {
        showFeedback('Please fill in time and mode', false, true);
        return;
    }
    
    // Check temperature only for HEAT/COOL modes
    if (mode !== 'off' && !temp) {
        showFeedback('Please specify temperature for ' + mode.toUpperCase() + ' mode', false, true);
        return;
    }
    
    const scheduleData = {
        time: time,
        temperature: mode === 'off' ? 70 : parseInt(temp), // Default temp for OFF mode
        mode: mode,
        days_of_week: days,
        enabled: true
    };
    
    fetchWithTimeout("http://blade:5000/set_schedule", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        body: JSON.stringify(scheduleData)
    }, timeout)
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => Promise.reject(err));
        }
        return response.json();
    })
    .then(data => {
        showFeedback('Schedule created successfully');
        // Clear form
        document.getElementById('schedule-time').value = '';
        document.getElementById('schedule-temp').value = '';
        displayScheduledItems();
    })
    .catch(error => {
        console.error('Error setting schedule:', error);
        if (error.message) {
            showFeedback(error.message, true);
        } else {
            showFeedback('Failed to create schedule', true);
        }
    });
}

// Function to initialize video feed
function initializeVideoFeed() {
    const video = document.getElementById('video');
    const videoFeedUrl = 'http://blade:5000/video_feed';
    
    // Set initial placeholder
    video.style.minHeight = '200px';
    
    function loadNextFrame() {
        const newFrameUrl = videoFeedUrl + '?t=' + new Date().getTime();
        const imgLoader = new Image();
        
        imgLoader.onload = () => {
            // Remove min-height once image loads successfully
            video.style.minHeight = '';
            video.src = newFrameUrl;
            setTimeout(loadNextFrame, 1000);
        };
        
        imgLoader.onerror = () => {
            console.error("Failed to load video frame, retrying...");
            // Keep trying but less frequently on error
            setTimeout(loadNextFrame, 5000);
        };
        
        imgLoader.src = newFrameUrl;
    }
    
    loadNextFrame();
}

// Function to reload page if needed
function reloadPageIfNeeded(error) {
    console.error('Initial request failed, reloading page:', error);
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

// Vision detection - simplified to just show current reading
let visionLastUpdateTime = null;

// Update the time since last vision update
function updateVisionTime() {
    if (visionLastUpdateTime) {
        const now = new Date();
        const secondsAgo = Math.max(0, Math.floor((now - visionLastUpdateTime) / 1000));
        document.getElementById('vision-last-update').textContent = secondsAgo + 's ago';
    }
}

// Update vision temperature data
function updateVisionData() {
    // First trigger a new vision reading by requesting the annotated image
    // This will cause Claude to read the temperature if enough time has passed
    fetch("/vision_annotated_image")
        .then(() => {
            // After triggering the reading, fetch the updated data
            return fetchWithTimeout("/vision_temperature_data", {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }, timeout);
        })
        .then(response => response.json())
        .then(data => {
        // Update current temperature and confidence
        const confElement = document.getElementById('vision-confidence');
        const tempElement = document.getElementById('vision-current-temp');
        
        if (data.confidence === 'STALE' || data.confidence === 'NO_DATA') {
            // Don't show stale or missing data
            tempElement.textContent = '--°F';
            tempElement.className = 'stat-value large error';
            confElement.textContent = data.confidence;
            confElement.className = 'stat-value error';
        } else if (data.current_temp !== null) {
            tempElement.textContent = data.current_temp + '°F';
            tempElement.className = 'stat-value large';
            confElement.textContent = data.confidence;
            confElement.className = 'stat-value ' + data.confidence.toLowerCase();
        }
        
        // Update last update time
        if (data.last_update) {
            visionLastUpdateTime = new Date(data.last_update);
            updateVisionTime();
        }
    })
    .catch(error => console.error('Error fetching vision data:', error));
}


// Function to check version
function checkVersion() {
    fetchWithTimeout("http://blade:5000/version", {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Accept': 'application/json'
        }
    }, timeout)
    .then(response => response.json())
    .then(data => {
        if (currentVersion === null) {
            // First time loading
            currentVersion = data.version;
            updateVersionBadge(currentVersion);
        } else if (currentVersion !== data.version) {
            // Version has changed
            showFeedback(`New version available: ${data.version}. Please refresh the page.`, false, true);
            updateVersionBadge(data.version, true);
        }
    })
    .catch(error => console.error('Error checking version:', error));
}

// Function to update version badge
function updateVersionBadge(version, hasUpdate = false) {
    const badge = document.querySelector('.version-badge');
    if (badge) {
        badge.textContent = `v${version}`;
        if (hasUpdate) {
            badge.style.backgroundColor = '#ff6b6b';
            badge.style.animation = 'pulse 1s infinite';
        }
    }
}

// Function to handle schedule mode change
function onScheduleModeChange() {
    const mode = document.getElementById('schedule-mode').value;
    const tempInput = document.getElementById('schedule-temp');
    const tempContainer = tempInput.parentElement;
    
    if (mode === 'off') {
        // Hide temperature input for OFF mode
        tempInput.style.display = 'none';
        tempInput.removeAttribute('required');
        tempInput.value = ''; // Clear the value
    } else {
        // Show temperature input for HEAT/COOL modes
        tempInput.style.display = 'inline-block';
        tempInput.setAttribute('required', 'required');
    }
}

// Initialize when DOM is loaded
window.onload = function() {
    checkServerHealth();
    checkVersion();
    
    // Update status every second
    setInterval(updateStatus, 1000);
    
    // Update schedules every 5 seconds
    setInterval(displayScheduledItems, 5000);
    
    // Check version every 30 seconds
    setInterval(checkVersion, 30000);
    
    // Initialize video feed
    initializeVideoFeed();
    
    // Add event listener for schedule mode changes
    const scheduleModeSelect = document.getElementById('schedule-mode');
    if (scheduleModeSelect) {
        scheduleModeSelect.addEventListener('change', onScheduleModeChange);
        // Initialize on page load
        onScheduleModeChange();
    }
    
    // Display schedules initially
    displayScheduledItems();
    
    // Update vision data every 30 seconds (to avoid calling Claude too frequently)
    setInterval(updateVisionData, 30000);
    
    // Update vision time display every second
    setInterval(updateVisionTime, 1000);
    
    // Initial vision update
    updateVisionData();
};