let currentTargetTemp;
let currentSetTemp;
let currentMode;
let currentTargetMode;
let userNotRequestingChange = true;
let userNotRequestingChangeMode = true;
let autoUpdatePaused = false; // New flag to pause auto-updates during user interactions

// Utility function to fetch with a timeout
function fetchWithTimeout(url, options, timeout = 1000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    return fetch(url, {
        ...options,
        signal: controller.signal
    }).finally(() => clearTimeout(id));
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
    }, 500)
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
    }, 500)
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
        }, 500)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            userNotRequestingChange = true;
            autoUpdatePaused = false; // Resume automatic updates after successful change
        })
        .catch(error => {
            console.error('Error sending temperature update:', error);
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
    }, 500)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        currentMode = data.current_mode.toLowerCase();
        if (currentTargetMode == null) {
            currentTargetMode = currentMode;
        }
        if (currentMode !== currentTargetMode && userNotRequestingChangeMode) {
            document.getElementById(currentMode + "-mode").checked = true;
            currentTargetMode = currentMode;
        }
    })
    .catch(error => console.error('Error fetching current mode:', error));
}

// Function to update the target mode based on user input
function updateTargetMode(radioButton) {
    userNotRequestingChangeMode = false;
    autoUpdatePaused = true; // Pause automatic updates during manual mode change
    currentTargetMode = radioButton.value.toLowerCase();
    sendModeUpdate(); // Immediately send the mode update
}

// Function to send a mode update to the server
function sendModeUpdate() {
    if (currentTargetMode !== currentMode) {
        fetchWithTimeout("http://10.0.0.54:5000/set_mode", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ mode: currentTargetMode })
        }, 500)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            currentMode = currentTargetMode;
            userNotRequestingChangeMode = true;
            autoUpdatePaused = false; // Resume automatic updates after successful change
        })
        .catch(error => {
            console.error('Error sending mode update:', error);
            autoUpdatePaused = false; // Resume updates even if there's an error
        });
    }
}

// Initialize the desired temperature and update the page every second
window.onload = function() {
    checkServerHealth();

    setInterval(updateTimeSinceLastAction, 1000);
    setInterval(updateCurrentMode, 1000);
    setInterval(updateDesiredTemperature, 1000);
    setInterval(updateTemperatureSettings, 1000);

    document.getElementById('increase-temp').addEventListener('click', () => {
        adjustTemperature(1);
        debouncedSendTemperatureUpdate();
    });

    document.getElementById('decrease-temp').addEventListener('click', () => {
        adjustTemperature(-1);
        debouncedSendTemperatureUpdate();
    });

    document.getElementById('light-btn').addEventListener('click', activateLight);

    initializeVideoFeed();
};
