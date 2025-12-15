// static/js/app.js (v1.1 - Chart.js Layout Fix)

let tempChart; 
let realTimeInterval, statsInterval;

function sendSuggestedReply(text) {
    document.getElementById('chat-input').value = text;
    sendMessage();
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('device-selector').addEventListener('change', handleDeviceSelection);
    document.getElementById('chat-input').addEventListener('keypress', e => e.key === 'Enter' && sendMessage());
    loadDevices();
});

async function loadDevices() {
    try {
        const response = await fetch('/api/devices');
        if (!response.ok) throw new Error('無法載入設備列表');
        const devices = await response.json();
        const selector = document.getElementById('device-selector');
        selector.innerHTML = '<option value="">-- 請選擇一個設備 --</option>';
        devices.forEach(device => { 
            if (!device.id) return; 
            const option = document.createElement('option'); 
            option.value = device.id; 
            option.textContent = device.name; 
            selector.appendChild(option); 
        });
        const defaultOption = Array.from(selector.options).find(opt => opt.textContent === 'MyTempSensor');
        if (defaultOption) { 
            defaultOption.selected = true; 
            selector.dispatchEvent(new Event('change')); 
        }
    } catch (error) { 
        console.error("載入設備時發生錯誤:", error); 
        alert('無法載入設備列表，請檢查後端服務是否已啟動。'); 
    }
}

async function addDevice() {
    const deviceNameInput = document.getElementById('new-device-name');
    const deviceName = deviceNameInput.value;
    if (!deviceName) { alert('請輸入設備名稱'); return; }
    try {
        const response = await fetch('/api/device', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ name: deviceName }) 
        });
        if(response.ok) { 
            alert('設備新增成功！'); 
            deviceNameInput.value = ''; 
            loadDevices(); 
        } else { 
            throw new Error('新增設備請求失敗');
        }
    } catch (error) {
        console.error("新增設備時發生錯誤:", error);
        alert('設備新增失敗！');
    }
}

function handleDeviceSelection(event) {
    const deviceId = event.target.value;
    if (realTimeInterval) clearInterval(realTimeInterval);
    if (statsInterval) clearInterval(statsInterval);
    if (deviceId) {
        document.getElementById('stats-container').style.display = 'block';
        loadChartData(deviceId);
        startRealTimeUpdates(deviceId); 
        const updateStats = () => loadStatistics(deviceId);
        updateStats(); 
        statsInterval = setInterval(updateStats, 60000);
    } else {
        document.getElementById('stats-container').style.display = 'none';
        document.getElementById('real-time-temp').textContent = '-- °C';
        document.getElementById('last-update-time').textContent = '';
        if(tempChart) tempChart.destroy();
    }
}

async function loadStatistics(deviceId) {
    try {
        const response = await fetch(`/api/device/${deviceId}/stats`);
        if (!response.ok) { 
            const err = await response.json(); 
            throw new Error(err.error || '獲取統計數據失敗'); 
        }
        const stats = await response.json();
        const na = 'N/A';
        document.getElementById('today-max').textContent = stats.today ? `${stats.today.max} °C` : na;
        document.getElementById('today-min').textContent = stats.today ? `${stats.today.min} °C` : na;
        document.getElementById('today-avg').textContent = stats.today ? `${stats.today.avg} °C` : na;
        document.getElementById('week-max').textContent = stats.week ? `${stats.week.max} °C` : na;
        document.getElementById('week-min').textContent = stats.week ? `${stats.week.min} °C` : na;
        document.getElementById('week-avg').textContent = stats.week ? `${stats.week.avg} °C` : na;
        document.getElementById('week-diff').textContent = stats.week ? `${stats.week.diff} °C` : na;
        document.getElementById('month-avg').textContent = stats.month_avg ? `${stats.month_avg} °C` : na;
        
        const tbody = document.getElementById('daily-breakdown-body');
        tbody.innerHTML = '';
        if (stats.daily_breakdown && stats.daily_breakdown.length > 0) {
            stats.daily_breakdown.forEach(day => {
                const row = `<tr><td>${day.date}</td><td>${day.avg} °C</td><td>${day.max} °C</td><td>${day.min} °C</td><td>${day.diff} °C</td></tr>`;
                tbody.innerHTML += row;
            });
        } else { 
            tbody.innerHTML = '<tr><td colspan="5">無每日數據</td></tr>'; 
        }
    } catch (error) { 
        console.error('載入統計數據時發生錯誤:', error); 
    }
}

function startRealTimeUpdates(deviceId) {
    const tempElement = document.getElementById('real-time-temp');
    const timeElement = document.getElementById('last-update-time');
    const fetchAndUpdate = async () => {
        try {
            const response = await fetch(`/api/device/${deviceId}/latest`);
            if (!response.ok) throw new Error('獲取最新數據失敗');
            const data = await response.json();
            if (data && data.temperature && data.temperature.length > 0) {
                const latestValue = parseFloat(data.temperature[0].value); 
                if (!isNaN(latestValue)) { 
                    tempElement.textContent = `${latestValue.toFixed(2)} °C`; 
                } else { 
                    tempElement.textContent = 'N/A'; 
                }
                timeElement.textContent = `最後更新: ${new Date().toLocaleTimeString()}`;
            } else { 
                tempElement.textContent = '無數據'; 
            }
        } catch (error) { 
            console.error('即時更新時發生錯誤:', error); 
            tempElement.textContent = '更新失敗'; 
        }
    };
    fetchAndUpdate(); 
    realTimeInterval = setInterval(fetchAndUpdate, 5000); 
}

// --- ✨✨ 這裡就是升級的地方！ ✨✨ ---
async function loadChartData(deviceId) {
    try {
        const response = await fetch(`/api/device/${deviceId}/history?key=temperature&agg=AVG&interval=3600000`);
        const data = await response.json();
        const chartData = data.temperature ? data.temperature.map(item => ({ x: item.ts, y: parseFloat(item.value) })).filter(item => !isNaN(item.y)) : [];
        const ctx = document.getElementById('tempChart').getContext('2d');
        if (tempChart) tempChart.destroy();
        tempChart = new Chart(ctx, { 
            type: 'line', 
            data: { datasets: [{ label: '每週溫度趨勢 (每小時平均)', data: chartData, borderColor: 'rgb(75, 192, 192)', tension: 0.1 }] }, 
            options: { 
                // ✨ 新增這兩行，告訴圖表要填滿容器，不要維持長寬比 ✨
                responsive: true,
                maintainAspectRatio: false,
                scales: { 
                    x: { type: 'time', time: { unit: 'day' } }, 
                    y: { beginAtZero: false } 
                } 
            } 
        });
    } catch(error) {
        console.error('載入圖表時發生錯誤:', error);
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value;
    const deviceId = document.getElementById('device-selector').value;
    const chatWindow = document.getElementById('chat-window');
    if (!question || !deviceId) { alert('請先選擇設備並輸入問題'); return; }

    const userMessageDiv = document.createElement('div');
    userMessageDiv.className = 'user-message';
    userMessageDiv.innerHTML = `<p><strong>您:</strong> ${question}</p>`;
    chatWindow.appendChild(userMessageDiv);
    
    input.value = '';
    chatWindow.scrollTop = chatWindow.scrollHeight;

    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'ai-message';
    thinkingDiv.innerHTML = `<p><strong>AI:</strong> 思考中...</p>`;
    chatWindow.appendChild(thinkingDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    try {
        const response = await fetch(`/ask?deviceId=${deviceId}&q=${encodeURIComponent(question)}`);
        const result = await response.json();
        chatWindow.removeChild(thinkingDiv);
        const answer = result.ai_analysis || `發生錯誤: ${result.error}`;
        
        const aiMessageDiv = document.createElement('div');
        aiMessageDiv.className = 'ai-message';
        aiMessageDiv.innerHTML = `<p><strong>AI:</strong> ${answer}</p>`;
        chatWindow.appendChild(aiMessageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;

    } catch (error) {
        console.error('發送訊息時發生錯誤:', error);
        chatWindow.removeChild(thinkingDiv);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'ai-message';
        errorDiv.innerHTML = `<p><strong>AI:</strong> 抱歉，與伺服器連線時發生錯誤。</p>`;
        chatWindow.appendChild(errorDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
}