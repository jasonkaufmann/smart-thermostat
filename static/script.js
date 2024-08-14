let currentTargetTemp;
let currentSetTemp;
let currentMode;
let currentTargetMode;
let userNotRequestingChange = true;
let userNotRequestingChangeMode = true;
let autoUpdatePaused = false; // New flag to pause auto-updates during user interactions
let timeout = 2000; // Timeout for fetch requests
// Utility function to fetch with a timeout
function fetchWithTimeout(url, options, timeout = 1000) {
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
            console.log('Temperature update response:', data);
            userNotRequestingChange = true;
            console.log('User not requesting temperature change:', userNotRequestingChange);
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
            console.log('Mode update response:', response);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            currentMode = currentTargetMode;
            document.getElementById("current-mode").innerText = currentMode.toUpperCase();
            console.log('Current mode updated to:', currentMode);
            userNotRequestingChangeMode = true;
            console.log('User not requesting mode change:', userNotRequestingChangeMode);
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
};
