let currentTargetTemp;
let currentSetTemp;
let currentMode;

// Function to check server readiness
function checkServerHealth() {
    console.log("Checking server health");

    fetch("http://10.0.0.54:5000/health", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for server health check");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Server is healthy, initializing desired temperature");
        initializeDesiredTemperature(); // Proceed with initialization
    })
    .catch(error => {
        console.error('Server health check failed, retrying:', error);
        setTimeout(checkServerHealth, 2000); // Retry after 2 seconds
    });
}

// Function to initialize the desired temperature
function initializeDesiredTemperature() {
    console.log("Initializing desired temperature");

    fetch("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for set_temperature");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for set_temperature:", data);
        currentSetTemp = data.desired_temperature;
        currentTargetTemp = currentSetTemp;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
        document.getElementById("desired-temperature").value = currentSetTemp;
        initializeVideoFeed(); // Initialize video feed after temperature setup
    })
    .catch(error => reloadPageIfNeeded(error));
}

// Function to update the time since last action
function updateTimeSinceLastAction() {
    console.log("Updating time since last action");

    fetch("http://10.0.0.54:5000/time_since_last_action", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for time_since_last_action");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for time_since_last_action:", data);
        document.getElementById("time-since-last-action").innerText = data.time_since_last_action + " seconds";
    })
    .catch(error => console.error('Error fetching time since last action:', error));
}

// Function to update the current mode
function updateCurrentMode() {
    console.log("Updating current mode");

    fetch("http://10.0.0.54:5000/current_mode", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for current_mode");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for current_mode:", data);
        document.getElementById("current-mode").innerText = data.current_mode;
        currentMode = data.current_mode.toLowerCase(); // Ensure mode is in lowercase
    })
    .catch(error => console.error('Error fetching current mode:', error));
}

// Function to update the desired temperature
function updateDesiredTemperature() {
    console.log("Updating desired temperature");

    fetch("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for set_temperature");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for set_temperature:", data);
        currentSetTemp = data.desired_temperature;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
    })
    .catch(error => console.error('Error fetching desired temperature:', error));
}

// Function to update heat and cool temperature settings
function updateTemperatureSettings() {
    console.log("Updating temperature settings");

    fetch("http://10.0.0.54:5000/temperature_settings", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log("Received response for temperature_settings");
        if (!response.ok) {
            console.error(`HTTP error! status: ${response.status}`);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Parsed JSON for temperature_settings:", data);
        document.getElementById("heat-temperature").innerText = data.current_heat_temp + "°F";
        document.getElementById("cool-temperature").innerText = data.current_cool_temp + "°F";
    })
    .catch(error => console.error('Error fetching temperature settings:', error));
}

// Function to adjust the temperature
function adjustTemperature(change) {
    console.log("Adjusting temperature by", change);
    currentTargetTemp += change;
    document.getElementById("desired-temperature").value = currentTargetTemp;
}

// Function to send the temperature update to the server
function sendTemperatureUpdate() {
    console.log("Sending temperature update to server");
    console.log("Current Set Temp:", currentSetTemp);
    console.log("Current Target Temp:", currentTargetTemp);

    if (currentTargetTemp !== currentSetTemp) {
        fetch("http://10.0.0.54:5000/set_temperature", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ temperature: currentTargetTemp })
        })
        .then(response => {
            console.log("Received response for temperature update");
            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => console.log('Temperature update response:', data))
        .catch(error => console.error('Error sending temperature update:', error));
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
const debouncedSendTemperatureUpdate = debounce(sendTemperatureUpdate, 5000);

// Function to activate the light
function activateLight() {
    console.log("Activating light");

    fetch("http://10.0.0.54:5000/activate_light", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    })
    .then(response => {
        console.log("Received response for light activation");
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

// Function to initialize video feed
function initializeVideoFeed() {
    console.log("Initializing video feed");

    setTimeout(() => {
        const video = document.getElementById('video');
        const videoFeedUrl = video.dataset.videoFeedUrl;
        console.log("Video feed URL:", videoFeedUrl);

        // Reload the video feed every 10 seconds using the evaluated URL
        setInterval(() => {
            console.log("Reloading video feed");
            video.src = videoFeedUrl + '?t=' + new Date().getTime();
        }, 10000); // Adjust interval if needed
    }, 5000); // 5-second delay to start video feed
}

// Initialize the desired temperature and update the page every second
window.onload = function() {
    console.log("Window loaded, starting initialization");

    checkServerHealth(); // Start with a server health check

    setInterval(updateTimeSinceLastAction, 1000);
    setInterval(updateCurrentMode, 1000);
    setInterval(updateDesiredTemperature, 1000);
    setInterval(updateTemperatureSettings, 1000); // Update heat and cool settings

    // Add event listeners for temperature buttons
    document.getElementById('increase-temp').addEventListener('click', () => {
        console.log("Increase temperature button clicked");
        adjustTemperature(1);
        debouncedSendTemperatureUpdate();
    });

    document.getElementById('decrease-temp').addEventListener('click', () => {
        console.log("Decrease temperature button clicked");
        adjustTemperature(-1);
        debouncedSendTemperatureUpdate();
    });

    // Add event listener for light button
    document.getElementById('light-btn').addEventListener('click', activateLight);
};
