// Bot management functionality

document.addEventListener('DOMContentLoaded', function() {
    loadBotList();
});

async function loadBotList() {
    try {
        const response = await fetch('/api/bots');
        const bots = await response.json();
        
        const select = document.getElementById('botSelect');
        
        bots.forEach(bot => {
            const option = document.createElement('option');
            option.value = bot.id;
            option.textContent = `${bot.name} (${bot.species})`;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading bot list:', error);
        document.getElementById('botDetails').innerHTML = 
            '<div style="color: red;">Error loading bot list</div>';
    }
}

async function loadBotDetails(botId) {
    if (!botId) {
        document.getElementById('botDetails').innerHTML = 
            '<div class="loading">Select a bot to manage</div>';
        return;
    }
    
    try {
        // Load bot details
        const botsResponse = await fetch('/api/bots');
        const bots = await botsResponse.json();
        const bot = bots.find(b => b.id == botId);
        
        // Load knowledge
        const knowledgeResponse = await fetch(`/api/bot/${botId}/knowledge`);
        const knowledge = await knowledgeResponse.json();
        
        const detailsContainer = document.getElementById('botDetails');
        detailsContainer.innerHTML = `
            <div class="management-section">
                <h3>📋 Bot Information</h3>
                <p><strong>Name:</strong> ${bot.name}</p>
                <p><strong>Full Name:</strong> ${bot.fullname}</p>
                <p><strong>Species:</strong> ${bot.species}</p>
                <p><strong>Created:</strong> ${new Date(bot.created_at).toLocaleDateString()}</p>
            </div>
            
            <div class="management-section">
                <h3>🧠 Knowledge Management</h3>
                <div class="add-form">
                    <input type="text" id="newFact" placeholder="Enter new fact...">
                    <button onclick="addKnowledge(${botId})">Add Fact</button>
                </div>
                
                <div id="knowledgeList">
                    <h4>Current Knowledge (${knowledge.length} facts):</h4>
                    ${knowledge.length === 0 ? 
                        '<p>No knowledge yet. Add some facts!</p>' : 
                        knowledge.map(item => `
                            <div class="knowledge-item">
                                <span>${item.fact}</span>
                                <button class="delete-btn" onclick="deleteKnowledge(${botId}, ${item.id})">Delete</button>
                            </div>
                        `).join('')
                    }
                </div>
            </div>
            
            <div class="management-section">
                <h3>🔧 Adjust Needs</h3>
                <p><em>Adjust the bot's current needs (0-100):</em></p>
                
                <div class="slider-group">
                    <label>Energy: <span class="slider-value" id="energyValue">50</span>%</label>
                    <input type="range" id="energySlider" min="0" max="100" value="50" 
                           oninput="updateSliderValue('energy', this.value)"
                           onchange="updateBotNeed(${botId}, 'energy', this.value)">
                </div>
                
                <div class="slider-group">
                    <label>Social: <span class="slider-value" id="socialValue">50</span>%</label>
                    <input type="range" id="socialSlider" min="0" max="100" value="50"
                           oninput="updateSliderValue('social', this.value)"
                           onchange="updateBotNeed(${botId}, 'social', this.value)">
                </div>
                
                <div class="slider-group">
                    <label>Curiosity: <span class="slider-value" id="curiosityValue">50</span>%</label>
                    <input type="range" id="curiositySlider" min="0" max="100" value="50"
                           oninput="updateSliderValue('curiosity', this.value)"
                           onchange="updateBotNeed(${botId}, 'curiosity', this.value)">
                </div>
                
                <button onclick="saveAllNeeds(${botId})" style="margin-top: 15px; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px;">
                    💾 Save All Changes
                </button>
            </div>

            <div class="management-section">
                <h3>📝 Recent Memories</h3>
                <div style="margin-bottom: 10px;">
                    <button class="memory-btn" data-type="all">All Memories</button>
                    <button class="memory-btn" data-type="weather">Weather Memories</button>
                    <button class="memory-btn" data-type="economic">Economic Memories</button>
                    <button class="memory-btn" data-type="conversation">Conversations</button>
                </div>
                <div id="memoriesList">
                    <div class="loading">Click a button to load memories</div>
                </div>
            </div>
        `;
        attachMemoryButtonListeners(botId);
    } catch (error) {
        console.error('Error loading bot details:', error);
        document.getElementById('botDetails').innerHTML = 
            '<div style="color: red;">Error loading bot details</div>';
    }
}

function attachMemoryButtonListeners(botId) {
    const memoryButtons = document.querySelectorAll('.memory-btn');
    memoryButtons.forEach(button => {
        // Remove any existing listeners first
        button.replaceWith(button.cloneNode(true));
    });
    
    // Get fresh references
    const freshButtons = document.querySelectorAll('.memory-btn');
    freshButtons.forEach(button => {
        button.addEventListener('click', function() {
            const memoryType = this.getAttribute('data-type');
            loadMemories(botId, memoryType);
        });
    });
}

function updateSliderValue(need, value) {
    document.getElementById(need + 'Value').textContent = value;
}

async function updateBotNeed(botId, need, value) {
    // This updates immediately as slider moves
    console.log(`Updating ${need} to ${value} for bot ${botId}`);
}

async function saveAllNeeds(botId) {
    const needs = {
        energy: document.getElementById('energySlider').value,
        social: document.getElementById('socialSlider').value,
        curiosity: document.getElementById('curiositySlider').value
    };
    
    try {
        const response = await fetch(`/api/bot/${botId}/needs`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(needs)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ Needs updated successfully!');
        } else {
            alert('❌ Error updating needs: ' + result.error);
        }
    } catch (error) {
        alert('❌ Error updating needs: ' + error.message);
    }
}

// Knowledge functions (same as before)
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
            loadBotDetails(botId); // Refresh
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
            loadBotDetails(botId); // Refresh
        } else {
            alert('Error deleting fact');
        }
    } catch (error) {
        alert('Error deleting fact: ' + error.message);
    }
}

async function loadMemories(botId, memoryType = 'all') {
    const memoriesContainer = document.getElementById('memoriesList');
    memoriesContainer.innerHTML = '<div class="loading">Loading memories...</div>';
    
    try {
        let url;
        if (memoryType === 'all') {
            url = `/api/bot/${botId}/memories`;
        } else {
            url = `/api/bot/${botId}/memories/${memoryType}`;
        }
        
        const response = await fetch(url);
        const memories = await response.json();
        
        if (memories.length === 0) {
            memoriesContainer.innerHTML = '<p>No memories found.</p>';
            return;
        }
        
        memoriesContainer.innerHTML = `
            <div style="max-height: 300px; overflow-y: auto;">
                ${memories.map(memory => {
                    // Determine color based on event_type
                    let color = '#95a5a6'; // default gray
                    if (memory.event_type === 'weather') color = '#3498db';
                    else if (memory.event_type === 'economic') color = '#2ecc71';
                    else if (memory.event_type === 'conversation') color = '#9b59b6';
                    
                    return `
                    <div style="padding: 8px; margin-bottom: 5px; background: #f8f9fa; border-radius: 5px; border-left: 3px solid ${color};">
                        <div style="font-size: 0.8em; color: #7f8c8d;">
                            ${new Date(memory.timestamp).toLocaleString()}
                            ${memory.event_type ? `<span style="margin-left: 10px; padding: 2px 6px; background: #ecf0f1; border-radius: 3px;">${memory.event_type}</span>` : ''}
                        </div>
                        <div>${memory.event}</div>
                    </div>
                    `;
                }).join('')}
            </div>
        `;
        
    } catch (error) {
        console.error('Error loading memories:', error);
        memoriesContainer.innerHTML = '<div style="color: red;">Error loading memories</div>';
    }
}