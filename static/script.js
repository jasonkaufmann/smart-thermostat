// script.js

let currentTargetTemp;
let currentSetTemp;
let currentMode;

// Function to initialize the desired temperature
// Function to initialize the desired temperature
function initializeDesiredTemperature() {
    fetch("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(data);
        currentSetTemp = data.desired_temperature;
        currentTargetTemp = currentSetTemp;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
        document.getElementById("desired-temperature").value = currentSetTemp;
    })
    .catch(error => console.error('Error fetching initial temperature:', error));

    fetch("http://10.0.0.54:5000/current_mode", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(data);
        currentMode = data.current_mode.toLowerCase(); // Ensure mode is in lowercase
        // Set the radio button to the current mode
        document.querySelector(`input[name="mode"][value="${currentMode}"]`).checked = true;
    })
    .catch(error => console.error('Error fetching current mode:', error));
}

// Function to update the time since last action
function updateTimeSinceLastAction() {
    fetch("http://10.0.0.54:5000/time_since_last_action", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        document.getElementById("time-since-last-action").innerText = data.time_since_last_action + " seconds";
    })
    .catch(error => console.error('Error fetching time since last action:', error));
}

// Function to update the current mode
function updateCurrentMode() {
    fetch("http://10.0.0.54:5000/current_mode", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        document.getElementById("current-mode").innerText = data.current_mode;
        currentMode = data.current_mode.toLowerCase(); // Ensure mode is in lowercase
    })
    .catch(error => console.error('Error fetching current mode:', error));
}


// Function to update the desired temperature
function updateDesiredTemperature() {
    fetch("http://10.0.0.54:5000/set_temperature", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        currentSetTemp = data.desired_temperature;
        document.getElementById("set-temperature").innerText = currentSetTemp + "°F";
    })
    .catch(error => console.error('Error fetching desired temperature:', error));
}

// Function to update heat and cool temperature settings
function updateTemperatureSettings() {
    fetch("http://10.0.0.54:5000/temperature_settings", {
        method: 'GET',
        mode: 'cors', // Ensure CORS mode is specified
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    })
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
}

// Function to send the temperature update to the server
function sendTemperatureUpdate() {
    console.log("Sending temperature update to server");
    console.log("Current Set Temp: " + currentSetTemp);
    console.log("Current Target Temp: " + currentTargetTemp);
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
            if (!response.ok) {
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
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => console.log('Light activation response:', data))
    .catch(error => console.error('Error activating light:', error));
}

// Initialize the desired temperature and update the page every second
window.onload = function() {
    setTimeout(() => {
        initializeDesiredTemperature();
        setInterval(updateTimeSinceLastAction, 1000);
        setInterval(updateCurrentMode, 1000);
        setInterval(updateDesiredTemperature, 1000);
        setInterval(updateTemperatureSettings, 1000); // Update heat and cool settings

        // Get the video feed URL from the data attribute
        const videoFeedUrl = document.getElementById('video').dataset.videoFeedUrl;

        // Reload the video feed every 3 seconds using the evaluated URL
        setInterval(() => {
            const video = document.getElementById('video');
            video.src = videoFeedUrl + '?t=' + new Date().getTime();
        }, 3000);

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
    }, 2000); // 2-second delay before initialization
};
