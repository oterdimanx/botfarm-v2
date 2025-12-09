        let mapData = null;
        let showInteractions = true;
        let selectedBotId = null;
        let appConfig = {};
        let airports = [];

        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                appConfig = await response.json();
            } catch (error) {
                console.error('Failed to load config, using defaults');
                appConfig = getDefaultConfig();
            }
        }
        
        // Color mappings
        const locationColors = {
            'plains': '#a8d5a2',
            'forest': '#2d5a27', 
            'mountain': '#8b7355',
            'city': '#ffd700',
            'water': '#1e90ff',
            'desert': '#f4a460'
        };
        
        const botColors = {
            1: '#3498db',
            2: '#e74c3c', 
            3: '#2ecc71',
            5: '#9b59b6'
        };
        
        async function loadMap() {
            try {
                const response = await fetch('/api/map/data');
                mapData = await response.json();
                renderMap();
            } catch (error) {
                console.error('Error loading map:', error);
            }
        }
        
        function renderMap() {
            if (!mapData) return;
            
            const botColors = appConfig.colors?.bots
            const locationColors = appConfig.colors?.terrain

            const grid = document.getElementById('mapGrid');
            const cellSize = mapData.map_info.cell_size;
            const width = mapData.map_info.width;
            const height = mapData.map_info.height;
            
            // Set grid size
            grid.style.gridTemplateColumns = `repeat(${width}, ${cellSize}px)`;
            grid.style.gridTemplateRows = `repeat(${height}, ${cellSize}px)`;
            grid.innerHTML = '';
            
            // Create empty grid cells (for terrain)
            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    const cell = document.createElement('div');
                    cell.className = 'map-cell';
                    cell.style.backgroundColor = '#a8d5a2'; // Default plains
                    cell.dataset.x = x;
                    cell.dataset.y = y;
                    
                    // Add coordinates tooltip
                    cell.title = `(${x}, ${y})`;
                    
                    grid.appendChild(cell);
                }
            }
            
            // ========== ADD THIS SECTION ==========
            // 1. FIRST: Set terrain colors for ALL cells
            if (mapData.terrain && locationColors) {
                mapData.terrain.forEach(terrainCell => {
                    const cell = document.querySelector(
                        `.map-cell[data-x="${terrainCell.x}"][data-y="${terrainCell.y}"]`
                    );
                    if (cell && locationColors[terrainCell.type]) {
                        cell.style.backgroundColor = locationColors[terrainCell.type];
                    }
                });
            }
            
            // 2. SECOND: Draw bot homes
            if (mapData.bot_homes && Array.isArray(mapData.bot_homes)) {
                mapData.bot_homes.forEach(home => {
                    if (home) {
                        const cell = document.querySelector(
                            `.map-cell[data-x="${home.x}"][data-y="${home.y}"]`
                        );
                        if (cell) {
                            const marker = document.createElement('div');
                            marker.className = 'home-marker';
                            marker.title = `Home of Bot ${home.id}`;
                            marker.style.cssText = `
                                position: absolute;
                                top: 2px;
                                left: 2px;
                                width: 12px;
                                height: 12px;
                                background: white;
                                border: 2px solid #3498db;
                                border-radius: 50%;
                                z-index: 15;
                                cursor: pointer;
                            `;
                            marker.onclick = (e) => {
                                e.stopPropagation();
                                showHomeInfo(home.id, home.x, home.y);
                            };
                            cell.appendChild(marker);
                        }
                    }
                });
            }
            // ========== END ADDED SECTION ==========
            
            // 3. THIRD: Place bots on map (existing code)
            mapData.bots.forEach(bot => {
                const cellIndex = bot.y * width + bot.x;
                const cell = grid.children[cellIndex];
                
                if (cell) {
                    // REMOVE this line - terrain already set above
                    // if (locationColors[bot.type]) {
                    //     cell.style.backgroundColor = locationColors[bot.type];
                    // }
                    
                    // Add bot marker (existing code)
                    const marker = document.createElement('div');
                    marker.className = 'bot-marker';
                    marker.style.backgroundColor = botColors[bot.id] || '#95a5a6';
                    marker.textContent = bot.id;
                    marker.title = `${bot.name}\nStatus: ${bot.status}\nLast seen: ${new Date(bot.last_seen).toLocaleTimeString()}`;
                    
                    marker.onclick = async function(e) {
                        e.stopPropagation();
                        selectedBotId = bot.id;
                        showBotInfo(bot);
                        if (showMovePaths) {
                            await drawBotMoveHistory(selectedBotId, pathStyle);
                        }
                        
                        if (showVisitedCells) {
                            highlightVisitedCells(selectedBotId);
                        }
                    };
                    
                    cell.appendChild(marker);
                }
            });
            
            // Show interactions if enabled
            if (showInteractions) {
                //console.log(mapData.interactions)
                mapData.interactions.forEach(interaction => {
                    const cellIndex = interaction.y * width + interaction.x;
                    const cell = grid.children[cellIndex];
                    
                    if (cell) {
                        const interactionMarker = document.createElement('div');
                        interactionMarker.className = 'interaction-marker';
                        interactionMarker.title = `Bots ${interaction.bot_ids.join(', ')} interacted here\n${new Date(interaction.last_interaction).toLocaleTimeString()}`;
                        cell.appendChild(interactionMarker);
                    }
                });
            }
            
            // Add click handler to show coordinates
            grid.addEventListener('click', (e) => {
                if (e.target.classList.contains('map-cell')) {
                    const cell = e.target;
                    const x = parseInt(cell.dataset.x);
                    const y = parseInt(cell.dataset.y);
                    
                    // Check if this cell has any bot's home
                    let homeBot = null;
                    //console.log(mapData.bot_homes)
                    if (mapData.bot_homes && Array.isArray(mapData.bot_homes)) {
                        // It's an array - check each home object
                        for (const home of mapData.bot_homes) {
                            if (home && home.x === x && home.y === y) {
                                // Use home.id, not array index!
                                const botId = home.id;
                                const bot = mapData.bots.find(b => b.id == botId);
                                homeBot = {
                                    id: botId,
                                    name: bot ? bot.name : `Bot ${botId}`
                                };
                                break;
                            }
                        }
                    }

                    if (homeBot) {
                        // Show home info
                        document.getElementById('botInfo').innerHTML = `
                            <h3>Location (${x}, ${y})</h3>
                            <div style="background: #E8F4FD; border-left: 4px solid #3498db; padding: 10px; margin: 10px 0;">
                                <strong>🏠 This is the home of ${homeBot.name}</strong>
                            </div>
                            <p><strong>Bots here:</strong></p>
                                <ul>
                                    ${mapData.bots.filter(bot => bot.x == x && bot.y == y)
                                        .map(bot => `<li>${bot.name} (ID: ${bot.id})</li>`)
                                        .join('') || '<li>None</li>'}
                                </ul>
                                <p><strong>Interactions at this location:</strong></p>
                                <div id="locationInteractions">
                                    ${renderLocationInteractions(x, y)}
                                </div>
                        `;
                    } else {
                        // Show regular location info
                        document.getElementById('botInfo').innerHTML = `
                            <h3>Location (${x}, ${y})</h3>
                            <p><strong>Bots here:</strong></p>
                            <ul>
                                ${mapData.bots.filter(bot => bot.x == x && bot.y == y)
                                    .map(bot => `<li>${bot.name} (ID: ${bot.id})</li>`)
                                    .join('') || '<li>None</li>'}
                            </ul>
                            <p><strong>Interactions at this location:</strong></p>
                            <div id="locationInteractions">
                                ${renderLocationInteractions(x, y)}
                            </div>
                            <button onclick="document.getElementById('botInfo').style.display='none'">Close</button>
                        `;
                    }

                    document.getElementById('botInfo').style.display = 'block';
                }
            });
        }

        function renderLocationInteractions(x, y) {
            // Filter interactions for this location
            const locationInteractions = mapData.interactions.filter(
                interaction => interaction.x == x && interaction.y == y
            );
            
            if (locationInteractions.length === 0) {
                return '<p>No interactions recorded at this location.</p>';
            }
            
            // Group interactions by bot pairs for better display
            const interactionGroups = {};
            
            locationInteractions.forEach(interaction => {
                const botIds = interaction.bot_ids.sort((a, b) => a - b);
                const key = botIds.join('-');
                
                if (!interactionGroups[key]) {
                    interactionGroups[key] = {
                        botIds: botIds,
                        botNames: interaction.bot_names || [],
                        interactions: []
                    };
                }
                
                interactionGroups[key].interactions.push({
                    time: interaction.last_interaction || interaction.timestamp,
                    type: interaction.type || 'interaction'
                });
            });
            
            // Generate HTML for each interaction group
            let html = `<p><strong>Total interactions:</strong> ${locationInteractions.length}</p>`;
            
            Object.values(interactionGroups).forEach(group => {
                // Get bot names
                const botNames = group.botNames.length > 0 
                    ? group.botNames.join(' & ')
                    : `Bots ${group.botIds.join(' & ')}`;
                
                html += `
                    <div style="
                        background: #F9F9F9;
                        border: 1px solid #EEE;
                        border-radius: 6px;
                        padding: 12px;
                        margin: 10px 0;
                    ">
                        <strong>${botNames}</strong>
                        <p><small>${group.interactions.length} interaction(s)</small></p>
                        <div style="max-height: 150px; overflow-y: auto;">
                            <table style="width: 100%; font-size: 12px;">
                                <thead>
                                    <tr>
                                        <th style="text-align: left;">Time</th>
                                        <th style="text-align: left;">Type</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${group.interactions.map(inter => `
                                        <tr>
                                            <td>${new Date(inter.time).toLocaleString()}</td>
                                            <td>${inter.type}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });
            
            return html;
        }

        function showBotInfo(bot) {
            document.getElementById('botInfo').innerHTML = `
                <h3>${bot.name}</h3>
                <p><strong>ID:</strong> ${bot.id}</p>
                <p><strong>Location:</strong> (${bot.x}, ${bot.y}) - ${bot.type}</p>
                <p><strong>Status:</strong> ${bot.status}</p>
                <p><strong>Home Address:</strong> ${bot.home_x}, ${bot.home_y}</p>
                <p><strong>Last seen:</strong> ${new Date(bot.last_seen).toLocaleString()}</p>
                <button onclick="document.getElementById('botInfo').style.display='none'">Close</button>
            `;
            document.getElementById('botInfo').style.display = 'block';
        }

        async function drawBotMoveHistory(botId) {

            // Get move history
            const response = await fetch(`/api/bot/${botId}/move-history`);
            const data = await response.json();
            // Clear previous paths
            document.querySelectorAll('.move-path').forEach(el => el.remove());
            
            // Draw each move
            data.moves.forEach((move, index) => {
                drawMovePath(move.from, move.to, index, '');
            });
        }

        function drawMovePath(from, to, index, style = 'dotted') {
            const container = document.querySelector('.map-container');
            const cellSize = 30;
            
            // Positions relative to container
            const fromX = ((from.x + 1) * cellSize) + (cellSize / 2);
            const fromY = ((from.y + 1) * cellSize) + (cellSize / 2);
            const toX = ((to.x + 1) * cellSize) + (cellSize / 2);
            const toY = ((to.y + 1) * cellSize) + (cellSize / 2);
            //debugCoordinates(from.x, from.y, `FROM (${from.x},${from.y})`, 'green');
            //debugCoordinates(to.x, to.y, `TO (${to.x},${to.y})`, 'red');

            const path = document.createElement('div');
            path.className = 'move-path';
            
            // Calculate line
            const dx = toX - fromX;
            const dy = toY - fromY;
            const length = Math.sqrt(dx*dx + dy*dy);
            const angle = Math.atan2(dy, dx) * (180 / Math.PI);
            
            const lineStyle = style === 'dotted' ? 
                `background: repeating-linear-gradient(
                    to right,
                    rgba(255, 100, 100, ${0.8 - index * 0.1}),
                    rgba(255, 100, 100, ${0.8 - index * 0.1}) 3px,
                    transparent 3px,
                    transparent 6px
                )` : 
                `background: rgba(255, 100, 100, ${0.8 - index * 0.1})`;
            
            path.style.cssText = `
                position: absolute;
                left: ${fromX}px;
                top: ${fromY}px;
                width: ${length}px;
                height: 2px;
                ${lineStyle};
                transform-origin: 0 0;
                transform: rotate(${angle}deg);
                pointer-events: none;
                z-index: 3;
            `;
            
            container.appendChild(path);
        }

        let showHistory = false;

        function toggleMoveHistory() {
            showHistory = !showHistory;
            const paths = document.querySelectorAll('.move-path');
            paths.forEach(p => p.style.display = showHistory ? 'block' : 'none');
        }

        function clearAllPaths() {
            document.querySelectorAll('.move-path').forEach(el => el.remove());
        }

        // Store last position and draw line when bot moves
        let lastPositions = {};

        function updateBotTrail(botId, newX, newY) {
            if (lastPositions[botId]) {
                // Draw line from last position to new position
                drawMovePath(lastPositions[botId], {x: newX, y: newY}, 0);
            }
            
            // Update last position
            lastPositions[botId] = {x: newX, y: newY};
        }

        function debugCoordinates(x, y, label, color = 'blue') {
            const container = document.querySelector('.map-container');
            const cellSize = 30; // Change if your cell size is different
            
            const marker = document.createElement('div');
            marker.style.cssText = `
                position: absolute;
                left: ${x * cellSize}px;
                top: ${y * cellSize}px;
                width: ${cellSize}px;
                height: ${cellSize}px;
                border: 2px solid ${color};
                background: transparent;
                z-index: 9998;
                pointer-events: none;
                display: flex;
                align-items: center;
                justify-content: center;
                color: ${color};
                font-size: 10px;
            `;
            marker.textContent = label;
            container.appendChild(marker);
        }

        function highlightVisitedCells(botId) {
            // Clear previous highlights
            document.querySelectorAll('.visited-cell').forEach(el => el.remove());
            
            // Get move history
            fetch(`/api/bot/${botId}/move-history`)
                .then(response => response.json())
                .then(data => {
                    // Get unique visited cells
                    const visited = new Set();
                    data.moves.forEach(move => {
                        visited.add(`${move.from.x},${move.from.y}`);
                        visited.add(`${move.to.x},${move.to.y}`);
                    });
                    
                    // Highlight each visited cell
                    visited.forEach(cellKey => {
                        const [x, y] = cellKey.split(',').map(Number);
                        const cell = document.querySelector(
                            `.map-cell[data-x="${x}"][data-y="${y}"]`
                        );
                        
                        if (cell) {
                            const highlight = document.createElement('div');
                            highlight.className = 'visited-cell';
                            highlight.style.cssText = `
                                position: absolute;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                background: rgba(100, 200, 255, 0.3);
                                z-index: 2;
                                pointer-events: none;
                            `;
                            cell.appendChild(highlight);
                        }
                    });
                });
        }

        let showVisitedCells = false;
        let showMovePaths = true;
        let pathStyle = 'dotted';

        function toggleVisitedCells() {
            showVisitedCells = !showVisitedCells;
            const cells = document.querySelectorAll('.visited-cell');
            cells.forEach(cell => cell.style.display = showVisitedCells ? 'block' : 'none');
            
            // If turning on and a bot is selected, highlight its visited cells
            if (showVisitedCells && selectedBotId) {
                highlightVisitedCells(selectedBotId);
            }
        }

        function toggleMovePaths() {
            showMovePaths = !showMovePaths;
            document.querySelectorAll('.move-path').forEach(path => {
                path.style.display = showMovePaths ? 'block' : 'none';
            });
        }

        function redrawBotPaths(botId, style) {
            // Clear existing paths
            document.querySelectorAll('.move-path').forEach(el => el.remove());
            
            // Redraw with new style
            if (showMovePaths && selectedBotId === botId) {
                drawBotMoveHistory(botId, style);
            }
        }

        function changePathStyle(style) {
            pathStyle = style;
            // Redraw all paths with new style
            if (selectedBotId) {
                redrawBotPaths(selectedBotId, style);
            }
        }

        function clearAllVisuals() {
            document.querySelectorAll('.visited-cell, .move-path').forEach(el => el.remove());
        }

        async function loadTerrainColors() {
            const response = await fetch('/api/map/terrain');
            const data = await response.json();
            const colorMap = appConfig.colors?.terrain
            
            data.terrain.forEach(cell => {
                const cellElement = document.querySelector(
                    `.map-cell[data-x="${cell.x}"][data-y="${cell.y}"]`
                );
                if (cellElement) {
                    cellElement.style.backgroundColor = colorMap[cell.type] || '#ccc';
                    cellElement.title = `${cell.type} (${cell.x},${cell.y})`;
                }
            });
        }

        function drawHomeCells(botHomes) {
            if (Array.isArray(botHomes)) {
                botHomes.forEach((home) => {
                    if (home) {
                        const cell = document.querySelector(
                            `.map-cell[data-x="${home.x}"][data-y="${home.y}"] `
                        );
                        
                        if (cell) {
                            const marker = document.createElement('div');
                            marker.className = 'home-marker';
                            marker.title = `Home of Bot ${home.id} (${home.name})`;
                            marker.style.cssText = `
                                position: absolute;
                                top: 2px;
                                left: 2px;
                                width: 10px;
                                height: 10px;
                                background: white;
                                border: 2px solid #3498db;
                                border-radius: 50%;
                                z-index: 10;
                                cursor: pointer;
                            `;
                            
                            marker.onclick = function(e) {
                                e.stopPropagation();
                                showHomeInfo(home.id, home.x, home.y);
                            };
                            
                            cell.appendChild(marker);
                            cell.style.boxShadow = 'inset 0 0 0 2px gold';
                        }
                    }
                });
            }
        }

        function showHomeInfo(botId, x, y) {
            // Find bot info
            const bot = mapData.bots.find(b => b.id == botId);
            const botName = bot ? bot.name : `Bot ${botId}`;
            
            // Update location card
            document.getElementById('botInfo').innerHTML = `
                <h3>🏠 Bot Home</h3>
                <p><strong>Location:</strong> (${x}, ${y})</p>
                <p><strong>Home of:</strong> ${botName} (ID: ${botId})</p>
                <p><strong>Home status:</strong> Active</p>
                
                <h4>Bots currently at this location:</h4>
                <ul>
                    ${mapData.bots.filter(b => b.x == x && b.y == y)
                        .map(b => `<li>${b.name} (ID: ${b.id})</li>`)
                        .join('') || '<li>None</li>'}
                </ul>
                
                <button onclick="document.getElementById('botInfo').style.display='none'">Close</button>
            `;
            document.getElementById('botInfo').style.display = 'block';
        }

        async function loadAirports() {
            try {
                const response = await fetch('/api/airports');
                airports = await response.json();
                drawAirports();
            } catch (error) {
                console.error('Error loading airports:', error);
            }
        }

        function drawAirports() {
            airports.forEach(airport => {
                const cell = document.querySelector(
                    `.map-cell[data-x="${airport.x}"][data-y="${airport.y}"]`
                );
                
                if (cell) {
                    // Remove old markers
                    cell.querySelectorAll('.airport-marker').forEach(m => m.remove());
                    
                    // Create marker
                    const marker = document.createElement('div');
                    marker.className = 'airport-marker';
                    marker.dataset.airportId = airport.id;
                    
                    // Dynamic title based on queue
                    const queueStatus = airport.queue.length > 0 
                        ? `Queue: ${airport.queue.length}/${airport.capacity}` 
                        : 'No queue';
                    
                    marker.title = `✈️ ${airport.name}\nFee: $${airport.fee}\n${queueStatus}`;
                    
                    // Color based on queue status
                    const bgColor = airport.queue.length > 0 ? '#e74c3c' : '#2980b9';
                    const borderColor = airport.queue.length > airport.capacity * 0.8 ? '#ff0000' : '#ffffff';
                    
                    marker.style.cssText = `
                        position: absolute;
                        bottom: 2px;
                        right: 2px;
                        width: ${12 + Math.min(airport.queue.length, 5)}px;
                        height: ${12 + Math.min(airport.queue.length, 5)}px;
                        background: ${bgColor};
                        border: 2px solid ${borderColor};
                        border-radius: 50%;
                        z-index: 25;
                        cursor: pointer;
                        font-size: 10px;
                        text-align: center;
                        line-height: ${12 + Math.min(airport.queue.length, 5)}px;
                        color: white;
                        font-weight: bold;
                        box-shadow: 0 0 5px rgba(0,0,0,0.5);
                    `;
                    
                    marker.textContent = airport.queue.length > 0 ? airport.queue.length : '✈';
                    
                    marker.onclick = (e) => {
                        e.stopPropagation();
                        showAirportInfo(airport);
                    };
                    
                    cell.appendChild(marker);
                    
                    // Highlight busy airports
                    if (airport.queue.length > 0) {
                        cell.style.boxShadow = 'inset 0 0 15px rgba(231, 76, 60, 0.5)';
                        cell.style.border = '2px solid #e74c3c';
                    }
                }
            });
        }

        function showAirportInfo(airport) {
            const queueList = airport.queue.map(botId => 
                `<li>Bot ${botId}${selectedBotId == botId ? ' (selected)' : ''}</li>`
            ).join('');
            
            document.getElementById('botInfo').innerHTML = `
                <h3>✈️ ${airport.name}</h3>
                <p><strong>Location:</strong> (${airport.x}, ${airport.y})</p>
                <p><strong>Usage fee:</strong> $${airport.fee}</p>
                <p><strong>Capacity:</strong> ${airport.queue.length}/${airport.capacity} bots</p>
                <p><strong>Destinations:</strong> ${airport.destinations.length} airports</p>
                
                <h4>Queue:</h4>
                ${queueList ? `<ul>${queueList}</ul>` : '<p>Empty</p>'}
                
                ${selectedBotId ? `
                    <button onclick="useAirport(${selectedBotId}, ${airport.id})">
                        Join Queue ($${airport.fee})
                    </button>
                ` : '<p>Select a bot first to use airport</p>'}
                
                <button onclick="document.getElementById('botInfo').style.display='none'">
                    Close
                </button>
            `;
            document.getElementById('botInfo').style.display = 'block';
        }

        async function useAirport(botId, airportId) {
            try {
                const response = await fetch(`/api/bot/${botId}/use_airport/${airportId}`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert(`Success! ${result.message}. Position in queue: ${result.position_in_queue}`);
                    // Refresh airport data
                    loadAirports();
                } else {
                    alert(`Error: ${result.error}`);
                }
            } catch (error) {
                console.error('Error using airport:', error);
                alert('Failed to use airport');
            }
        }

        // Called when bot moves (in map update)
        // updateBotTrail(bot.id, newX, newY);
        function refreshMap() {
            loadConfig().then(() => {
                loadMap();
                loadTerrainColors();
                if (mapData.bot_homes){
                    drawHomeCells(mapData.bot_homes)
                }
                else {
                    console.log('no bot homes found')
                }
                loadAirports();
            });
        }
        
        function toggleInteractions() {
            showInteractions = !showInteractions;
            renderMap();
            if (mapData.bot_homes){
                drawHomeCells(mapData.bot_homes)
                loadAirports();
            }
            else {
                console.log('no bot homes found')
            }
        }
        
        // Auto-refresh
        document.getElementById('autoRefresh').addEventListener('change', function(e) {
            if (e.target.checked) {
                autoRefreshInterval = setInterval(loadMap, 15000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        });
        
        // Zoom control
        document.getElementById('zoom').addEventListener('input', function(e) {
            const size = parseInt(e.target.value);
            mapData.map_info.cell_size = size;
            renderMap();
            if (mapData && mapData.bot_homes) {
                drawHomeCells(mapData.bot_homes);
            }
            else {
                console.log('no bot homes found')
            }
        });
        
        // Initial load
        loadConfig().then(() => {

            if (mapData && mapData.bot_homes) {
                drawHomeCells(mapData.bot_homes);
            }

            loadMap()
            loadTerrainColors()
            loadAirports();
        });
        let autoRefreshInterval = setInterval(async () => {

            await loadConfig().then(() => {
                loadMap()
                loadTerrainColors()
                drawHomeCells(mapData.bot_homes)
                loadAirports();
            });
            if (mapData && mapData.bot_homes) {
                drawHomeCells(mapData.bot_homes);
            }
            else {
                console.log('no bot homes found')
            }
            
        }, 15000);