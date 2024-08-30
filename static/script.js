let scheduledItems = []; // Array to store scheduled items
let currentTargetTemp;
let currentSetTemp;
let currentMode;
let currentTargetMode;
let userNotRequestingChange = true;
let userNotRequestingChangeMode = true;
let autoUpdatePaused = false; // New flag to pause auto-updates during user interactions
let timeout = 10000; // Timeout for fetch requests

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
    fetchWithTimeout("http://10.0.0.54:5000/health", {
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
        initializeDesiredTemperature(); // Proceed with initialization
    })
    .catch(error => {
        console.error('Server health check failed, retrying:', error);
        setTimeout(checkServerHealth, 2000); // Retry after 2 seconds
    });
}

// Function to initialize the desired temperature
function initializeDesiredTemperature() {
    fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
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
    .then(data => {
        currentSetTemp = data.desired_temperature;
        currentTargetTemp = currentSetTemp;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
        document.getElementById("desired-temperature").value = currentSetTemp;
    })
    .catch(error => reloadPageIfNeeded(error));
}

// Function to update the time since last action
function updateTimeSinceLastAction() {
    fetchWithTimeout("http://10.0.0.54:5000/time_since_last_action", {
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
        document.getElementById("time-since-last-action").innerText = data.time_since_last_action + " seconds";
    })
    .catch(error => console.error('Error fetching time since last action:', error));
}

// Function to update the desired temperature
function updateDesiredTemperature() {
    if (autoUpdatePaused) return; // Skip update if paused
    fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
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
    .then(data => {
        currentSetTemp = data.desired_temperature;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
        if (currentSetTemp !== currentTargetTemp && userNotRequestingChange) {
            currentTargetTemp = currentSetTemp;
            document.getElementById("desired-temperature").value = currentSetTemp;
        }
    })
    .catch(error => console.error('Error fetching desired temperature:', error));
}

// Function to update heat and cool temperature settings
function updateTemperatureSettings() {
    fetchWithTimeout("http://10.0.0.54:5000/temperature_settings", {
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
    .then(data => {
        document.getElementById("heat-temperature").innerText = data.current_heat_temp + "°F";
        document.getElementById("cool-temperature").innerText = data.current_cool_temp + "°F";
    })
    .catch(error => console.error('Error fetching temperature settings:', error));
}

// Function to adjust the temperature
function adjustTemperature(change) {
    currentTargetTemp += change;
    document.getElementById("desired-temperature").value = currentTargetTemp;
    userNotRequestingChange = false;
    autoUpdatePaused = true; // Pause automatic updates during manual adjustment
}

// Function to send the temperature update to the server
function sendTemperatureUpdate() {
    if (currentTargetTemp !== currentSetTemp) {
        console.log('Sending temperature update:', currentTargetTemp);
        fetchWithTimeout("http://10.0.0.54:5000/set_temperature", {
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
            userNotRequestingChange = true;
            autoUpdatePaused = false; // Resume automatic updates after successful change
            return response.json();
        })
        .catch(error => {
            console.error('Error sending temperature update:', error);
            autoUpdatePaused = false; // Resume updates even if there's an error
        });
    }
}

// Function to send a mode update to the server
function sendModeUpdate() {
    if (currentTargetMode !== currentMode) {
        console.log('Sending mode update:', currentTargetMode);
        fetchWithTimeout("http://10.0.0.54:5000/set_mode", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ mode: currentTargetMode })
        }, timeout)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            currentMode = currentTargetMode;
            document.getElementById("current-mode").innerText = currentMode.toUpperCase();
            userNotRequestingChangeMode = true;
            autoUpdatePaused = false; // Resume automatic updates after successful change
            return response.json();
        })
        .catch(error => {
            console.error('Error sending mode update:', error);
            autoUpdatePaused = false; // Resume updates even if there's an error
        });
    }
}

// Function to update the current mode
function updateCurrentMode() {
    if (autoUpdatePaused) return; // Skip update if paused
    fetchWithTimeout("http://10.0.0.54:5000/current_mode", {
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
    .then(data => {
        currentMode = data.current_mode.toLowerCase(); // Ensure mode is in lowercase
        if (currentTargetMode == null) {
            currentTargetMode = currentMode; // Initialize target mode if not set
        }
        if (currentMode !== currentTargetMode && userNotRequestingChangeMode) {
            document.getElementById(currentMode + "-mode").checked = true; // Update the radio button
            document.getElementById("current-mode").innerText = currentMode.toUpperCase(); // Update the current mode
            currentTargetMode = currentMode; // Update the target mode to the current mode
        }
    })
    .catch(error => console.error('Error fetching current mode:', error));
}

// Function to update the target mode based on user input
function updateTargetMode(radioButton) {
    userNotRequestingChangeMode = false;
    autoUpdatePaused = true; // Pause automatic updates during manual mode change
    currentTargetMode = radioButton.value.toLowerCase(); // Ensure mode is in lowercase
    sendModeUpdate(); // Immediately send the mode update
}

// Function to fetch scheduled events from the server
function fetchScheduledEvents() {
    fetchWithTimeout("http://10.0.0.54:5000/get_scheduled_events", {
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
    .then(data => {
        scheduledItems = data; // Update the local array with fetched data
        displayScheduledItems(); // Refresh the display with new data
    })
    .catch(error => console.error('Error fetching scheduled events:', error));
}

// Function to display scheduled items
function displayScheduledItems() {
    const scheduledItemsContainer = document.getElementById('scheduled-items');
    scheduledItemsContainer.innerHTML = ''; // Clear existing items

    scheduledItems.forEach(item => { // Use each item's unique id directly from the server
        const scheduleItemDiv = document.createElement('div');
        scheduleItemDiv.classList.add('schedule-item');

        const scheduleInfo = document.createElement('span');
        scheduleInfo.textContent = `Time: ${item.time}, Temp: ${item.temperature}°F, Mode: ${item.mode.toUpperCase()}`;

        const enableCheckbox = document.createElement('input');
        enableCheckbox.type = 'checkbox';
        enableCheckbox.checked = item.enabled;
        enableCheckbox.onchange = () => toggleScheduleEnable(item.id, enableCheckbox.checked); // Use item.id instead of index

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.onclick = () => deleteScheduledItem(item.id); // Use item.id instead of index

        scheduleItemDiv.appendChild(scheduleInfo);
        scheduleItemDiv.appendChild(enableCheckbox);
        scheduleItemDiv.appendChild(deleteButton);

        scheduledItemsContainer.appendChild(scheduleItemDiv);
    });
}

// Function to toggle the enable state of a scheduled item
function toggleScheduleEnable(id, enabled) {
    // Find the item in the array and update its enabled state
    const item = scheduledItems.find(event => event.id === id);
    if (item) {
        item.enabled = enabled;
        console.log(`Schedule with ID ${id} enabled: ${enabled}`);

        // Send update to server
        const scheduleData = { enabled: enabled };

        fetchWithTimeout(`http://10.0.0.54:5000/update_schedule/${id}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(scheduleData)
        }, timeout)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            console.log('Schedule updated successfully on server');
        })
        .catch(error => console.error('Error updating schedule on server:', error));
    }
}

// Function to delete a scheduled item
function deleteScheduledItem(id) {
    // Send delete request to server
    fetchWithTimeout(`http://10.0.0.54:5000/delete_schedule/${id}`, {
        method: "DELETE",
        headers: {
            "Accept": "application/json"
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log(`Schedule with ID ${id} deleted successfully from server`);
        
        // If successful, remove the item from the array and refresh display
        scheduledItems = scheduledItems.filter(event => event.id !== id); // Remove the item by id
        displayScheduledItems(); // Refresh the display
    })
    .catch(error => console.error('Error deleting schedule from server:', error));
}

// Function to submit the schedule
function submitSchedule() {
    const time = document.getElementById('schedule-time').value;
    const temp = document.getElementById('schedule-temp').value;
    const mode = document.getElementById('schedule-mode').value;

    if (time && temp && mode) {
        const scheduleData = {
            time: time,
            temperature: parseInt(temp),
            mode: mode,
            enabled: true // Automatically set new schedules to enabled
        };

        fetchWithTimeout("http://10.0.0.54:5000/set_schedule", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(scheduleData)
        }, timeout)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Schedule set successfully:', data);
            alert('Schedule set successfully!');
            fetchScheduledEvents(); // Refresh the list after setting a new schedule
        })
        .catch(error => console.error('Error setting schedule:', error));
    } else {
        alert('Please fill all fields to set a schedule.');
    }
}

// Debounce function to limit the rate of function execution
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

// Debounced version of sendTemperatureUpdate to control frequency
const debouncedSendTemperatureUpdate = debounce(sendTemperatureUpdate, 1000);

// Function to activate the light
function activateLight() {
    fetchWithTimeout("http://10.0.0.54:5000/activate_light", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    }, timeout)
    .then(response => {
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => console.log('Light activation response:', data))
    .catch(error => console.error('Error activating light:', error));
}

// Function to reload the page if initial requests fail
function reloadPageIfNeeded(error) {
    console.error('Initial request failed, reloading page:', error);
    setTimeout(() => {
        window.location.reload();
    }, 1000); // Delay for 1 second before reloading
}

// Function to change the button color temporarily
function changeButtonColor() {
    const lightButton = document.getElementById('light-btn');
    
    // Add the yellow background class
    lightButton.classList.add('yellow-bg');

    // Remove the yellow background class after 3 seconds
    setTimeout(() => {
        lightButton.classList.remove('yellow-bg');
    }, 3000);
}

// Function to initialize the video feed
function initializeVideoFeed() {
    const video = document.getElementById('video');
    const videoFeedUrl = video.dataset.videoFeedUrl;

    // Function to load the next video frame
    function loadNextFrame() {
        const newFrameUrl = videoFeedUrl + '?t=' + new Date().getTime();

        // Create a new image object to load the frame
        const imgLoader = new Image();

        imgLoader.onload = () => {
            video.src = newFrameUrl; // Update the video source only after loading
            setTimeout(loadNextFrame, 5000); // Load the next frame after 1 second
        };

        imgLoader.onerror = () => {
            console.error("Failed to load video frame, retrying...");
            setTimeout(loadNextFrame, 5000); // Retry loading the frame after 1 second
        };

        // Start loading the new frame
        imgLoader.src = newFrameUrl;
    }

    // Load the first frame to start the process
    loadNextFrame();
}

// Initialize the desired temperature and update the page every second
window.onload = function() {
    checkServerHealth(); // Start with a server health check

    setInterval(updateTimeSinceLastAction, 1000);
    setInterval(updateCurrentMode, 1000);
    setInterval(updateDesiredTemperature, 1000);
    setInterval(updateTemperatureSettings, 1000); // Update heat and cool settings

    // Add event listeners for temperature buttons
    document.getElementById('increase-temp').addEventListener('click', () => {
        adjustTemperature(1);
        debouncedSendTemperatureUpdate();
    });

    document.getElementById('decrease-temp').addEventListener('click', () => {
        adjustTemperature(-1);
        debouncedSendTemperatureUpdate();
    });

    // Add event listener for light button
    document.getElementById('light-btn').addEventListener('click', activateLight);

    initializeVideoFeed(); // Initialize video feed after temperature setup

    displayScheduledItems(); // Display any existing scheduled items

    // Poll the server every 10 seconds for new scheduled events
    setInterval(fetchScheduledEvents, 10000);
};
