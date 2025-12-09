// Wait for page to load
window.economyChart = null
window.transactionChart = null
window.weatherChart = null;

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    setInterval(loadDashboard, 10000); // Refresh every 10 seconds
});

function updateTimestamp() {
    const now = new Date();
    document.getElementById('updateTime').textContent = now.toLocaleTimeString();
}

async function loadDashboard() {
    try {
        await loadOverview();
        await loadCharts();
        await loadWeather();
        await loadWeatherChart();
        await loadBotStatus();
        await loadPersonalities();
        updateTimestamp();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadOverview() {
    const response = await fetch('/api/overview');
    const data = await response.json();
    
    const overview = document.getElementById('overview');
    if (data.latest_cycle) {
        overview.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">Current Cycle</div>
                <div class="stat-value">${data.latest_cycle.cycle_number}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Total Currency</div>
                <div class="stat-value">${data.latest_cycle.total_currency.toFixed(0)}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Transactions</div>
                <div class="stat-value">${data.latest_cycle.total_transactions}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Active Bots</div>
                <div class="stat-value">${data.bot_count}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Total Cycles</div>
                <div class="stat-value">${data.total_cycles}</div>
            </div>
        `;
    } else {
        overview.innerHTML = '<div class="loading">No data available yet</div>';
    }
}

async function loadCharts() {
    const response = await fetch('/api/recent_cycles');
    const cycles = await response.json();
    
    if (cycles.length === 0) return;
    
    // Reverse to show chronological order
    cycles.reverse();
    
    // Economy Chart
    const economyCtx = document.getElementById('economyChart').getContext('2d');
    if (window.economyChart) window.economyChart.destroy();
    window.economyChart = new Chart(economyCtx, {
        type: 'line',
        data: {
            labels: cycles.map(c => `Cycle ${c.cycle_number}`),
            datasets: [{
                label: 'Total Currency',
                data: cycles.map(c => c.total_currency),
                borderColor: '#27ae60',
                backgroundColor: 'rgba(39, 174, 96, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Wealth Growth Over Time'
                }
            }
        }
    });
    
    // Transaction Chart
    const transactionCtx = document.getElementById('transactionChart').getContext('2d');
    if (window.transactionChart) window.transactionChart.destroy();
    window.transactionChart = new Chart(transactionCtx, {
        type: 'bar',
        data: {
            labels: cycles.map(c => `Cycle ${c.cycle_number}`),
            datasets: [{
                label: 'Transactions',
                data: cycles.map(c => c.total_transactions),
                backgroundColor: '#3498db',
                borderColor: '#2980b9',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Economic Activity'
                }
            }
        }
    });
}

async function loadBotStatus() {
    const response = await fetch('/api/current_bot_status');
    const bots = await response.json();
    
    const container = document.getElementById('botStatus');
    
    if (bots.length === 0) {
        container.innerHTML = '<div class="loading">No bot data available yet</div>';
        return;
    }
    
    container.innerHTML = bots.map(bot => `
        <div class="bot-card">
            <h3>${bot.bot_name}</h3>
            
            <div class="need-item">
                <div class="need-label">
                    <span>💰 Balance</span>
                    <span>${bot.balance.toFixed(1)}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill balance-fill" style="width: ${Math.min(bot.balance / 2, 100)}%"></div>
                </div>
            </div>
            
            <div class="need-item">
                <div class="need-label">
                    <span>⚡ Energy</span>
                    <span>${bot.energy.toFixed(0)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill energy-fill" style="width: ${bot.energy}%"></div>
                </div>
            </div>
            
            <div class="need-item">
                <div class="need-label">
                    <span>💬 Social</span>
                    <span>${bot.social.toFixed(0)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill social-fill" style="width: ${bot.social}%"></div>
                </div>
            </div>
            
            <div class="need-item">
                <div class="need-label">
                    <span>🔍 Curiosity</span>
                    <span>${bot.curiosity.toFixed(0)}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill curiosity-fill" style="width: ${bot.curiosity}%"></div>
                </div>
            </div>
        </div>
    `).join('');
}

async function loadPersonalities() {
    const response = await fetch('/api/bot_personalities');
    const personalities = await response.json();
    
    const container = document.getElementById('personalities');
    
    if (Object.keys(personalities).length === 0) {
        container.innerHTML = '<div class="loading">No personality data available</div>';
        return;
    }
    
    container.innerHTML = Object.entries(personalities).map(([botName, traits]) => `
        <div class="bot-card">
            <h3>${botName}</h3>
            <div class="personality-grid">
                ${Object.entries(traits)
                    .filter(([trait, value]) => 
                        ['generosity', 'ambition', 'risk_taking', 'empathy', 'curiosity', 'openness'].includes(trait)
                    )
                    .map(([trait, value]) => `
                    <div class="trait-item">
                        <div class="trait-name">${trait.replace('_', ' ')}</div>
                        <div class="trait-value">${value.toFixed(2)}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

async function loadBotManagement() {
    try {
        const response = await fetch('/api/bots');
        const bots = await response.json();
        
        const container = document.getElementById('botManagement');
        
        if (bots.length === 0) {
            container.innerHTML = '<div class="loading">No bots available</div>';
            return;
        }
        
        container.innerHTML = `
            <div style="margin-bottom: 20px;">
                <label><strong>Select Bot:</strong></label>
                <select id="botSelector" onchange="loadBotDetails(this.value)" style="margin-left: 10px; padding: 5px;">
                    <option value="">Choose a bot...</option>
                    ${bots.map(bot => `<option value="${bot.id}">${bot.name}</option>`).join('')}
                </select>
            </div>
            <div id="botDetails"></div>
        `;
    } catch (error) {
        console.error('Error loading bot management:', error);
        document.getElementById('botManagement').innerHTML = 
            '<div style="color: red;">Error loading bot management</div>';
    }
}

async function loadBotDetails(botId) {
    if (!botId) {
        document.getElementById('botDetails').innerHTML = '';
        return;
    }
    
    try {
        // Load bot knowledge
        const knowledgeResponse = await fetch(`/api/bot/${botId}/knowledge`);
        const knowledge = await knowledgeResponse.json();
        
        const detailsContainer = document.getElementById('botDetails');
        detailsContainer.innerHTML = `
            <div class="bot-management-section">
                <h3>🧠 Knowledge Management</h3>
                <div style="margin-bottom: 15px;">
                    <input type="text" id="newFact" placeholder="Enter new fact..." style="padding: 8px; width: 300px;">
                    <button onclick="addKnowledge(${botId})" style="padding: 8px 15px; margin-left: 10px;">Add Fact</button>
                </div>
                
                <div id="knowledgeList">
                    ${knowledge.map(item => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee;">
                            <span>${item.fact}</span>
                            <button onclick="deleteKnowledge(${botId}, ${item.id})" style="color: red; border: none; background: none; cursor: pointer;">❌</button>
                        </div>
                    `).join('')}
                    ${knowledge.length === 0 ? '<p>No knowledge yet.</p>' : ''}
                </div>
            </div>
            
            <div class="bot-management-section">
                <h3>🔧 Needs Adjustment</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div>
                        <label>Energy:</label>
                        <input type="range" id="energySlider" min="0" max="100" value="50" onchange="updateNeed(${botId}, 'energy', this.value)">
                        <span id="energyValue">50</span>%
                    </div>
                    <div>
                        <label>Social:</label>
                        <input type="range" id="socialSlider" min="0" max="100" value="50" onchange="updateNeed(${botId}, 'social', this.value)">
                        <span id="socialValue">50</span>%
                    </div>
                    <div>
                        <label>Curiosity:</label>
                        <input type="range" id="curiositySlider" min="0" max="100" value="50" onchange="updateNeed(${botId}, 'curiosity', this.value)">
                        <span id="curiosityValue">50</span>%
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Error loading bot details:', error);
    }
}

async function addKnowledge(botId) {
    const factInput = document.getElementById('newFact');
    const fact = factInput.value.trim();
    
    if (!fact) {
        alert('Please enter a fact');
        return;
    }
    
    try {
        const response = await fetch(`/api/bot/${botId}/knowledge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fact: fact })
        });
        
        const result = await response.json();
        
        if (result.success) {
            factInput.value = '';
            loadBotDetails(botId); // Refresh the list
        } else {
            alert('Error adding fact: ' + result.error);
        }
    } catch (error) {
        alert('Error adding fact: ' + error.message);
    }
}

async function deleteKnowledge(botId, knowledgeId) {
    if (!confirm('Are you sure you want to delete this knowledge?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/bot/${botId}/knowledge/${knowledgeId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            loadBotDetails(botId); // Refresh the list
        } else {
            alert('Error deleting fact');
        }
    } catch (error) {
        alert('Error deleting fact: ' + error.message);
    }
}

async function updateNeed(botId, needName, value) {
    // Update the displayed value
    document.getElementById(needName + 'Value').textContent = value;
    
    try {
        const response = await fetch(`/api/bot/${botId}/needs`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [needName]: value })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            console.error('Error updating need:', result.error);
        }
    } catch (error) {
        console.error('Error updating need:', error);
    }
}

async function loadWeather() {
    try {
        const response = await fetch('/api/weather');
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const weather = await response.json();
        
        const container = document.getElementById('weatherInfo');
        
        if (weather.error) {
            container.innerHTML = `<div class="loading">${weather.error}</div>`;
            return;
        }
        
        // Weather effects explanation
        let effects = '';
        if (weather.temperature < 10) {
            effects = '❄️ Bots conserving energy';
        } else if (weather.temperature > 25) {
            effects = '☀️ Bots seeking social connections';
        } else if (weather.condition && weather.condition.toLowerCase().includes('rain')) {
            effects = '🌧️ Bots more curious, less social';
        } else if (weather.condition && weather.condition.toLowerCase().includes('sun')) {
            effects = '😊 Bots in better mood';
        }
        
        container.innerHTML = `
            <div class="weather-display">
                <div style="font-size: 2em; margin-bottom: 10px;">${weather.temperature}°C</div>
                <div><strong>${weather.location || 'Unknown location'}</strong></div>
                <div>${weather.condition || 'Unknown conditions'}</div>
                <div>Humidity: ${weather.humidity || 'Unknown'}%</div>
                ${effects ? `<div style="margin-top: 10px; font-style: italic; color: #3498db;">${effects}</div>` : ''}
                <div style="font-size: 0.8em; color: #7f8c8d; margin-top: 10px;">
                    Updated: ${new Date(weather.collected_at).toLocaleTimeString()}
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading weather:', error);
        document.getElementById('weatherInfo').innerHTML = 
            '<div class="loading">Weather data unavailable</div>';
    }
}

async function loadWeatherChart() {
    try {
        const response = await fetch('/api/weather_history');
        
        // Check if response is OK
        if (!response.ok) {
            console.warn('Weather history API error:', response.status);
            return;
        }
        
        const weatherHistory = await response.json();
        
        // Check if we have data
        if (!weatherHistory || weatherHistory.length === 0) {
            console.log('No weather history data available yet');
            return;
        }
        
        // Reverse to show chronological order
        weatherHistory.reverse();
        
        // Create temperature chart
        const weatherCtx = document.getElementById('weatherChart').getContext('2d');
        
        if (window.weatherChart) {
            window.weatherChart.destroy();
        }
        
        window.weatherChart = new Chart(weatherCtx, {
            type: 'line',
            data: {
                labels: weatherHistory.map(w => {
                    // Handle missing time data
                    if (w.time) {
                        return new Date(w.time).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
                    }
                    return '';
                }),
                datasets: [{
                    label: 'Temperature (°C)',
                    data: weatherHistory.map(w => w.temperature || 0),
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Temperature Over Time'
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error loading weather chart:', error);
        // Don't show error in UI - just log it
    }
}

async function updateInteractions() {
    const response = await fetch('/api/map/interactions/recent');
    const interactions = await response.json();
    
    if (interactions.length > 0) {
        const html = interactions.map(i => 
            `<div class="interaction-item">
                Bot ${i.bot_id} interacted at (${i.location[0]},${i.location[1]})
            </div>`
        ).join('');
        document.getElementById('interactionList').innerHTML = html;
    }
}

// Update every 10 seconds
setInterval(updateInteractions, 10000);
updateInteractions();