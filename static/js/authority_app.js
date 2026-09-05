// SafeTrail — Regional Authority Operations Center Script

let authMap = null;
let touristMarkers = {};
let sosMarkers = {};
let zoneLayers = [];
let telemetryInterval = null;
let lastKnownSOSCount = 0;

// Chart.js instances
let incidentTypeChart = null;
let zoneDensityChart = null;

// Telemetry cache
let currentTelemetry = {
    tourists: [],
    sos_events: [],
    incidents: [],
    zones: [],
    pois: [],
    analytics: {}
};

document.addEventListener('DOMContentLoaded', () => {
    initAuthorityMap();
    initCharts();
    pollTelemetry();
    telemetryInterval = setInterval(() => pollTelemetry(false), 5000);
});

// Initialize Leaflet Map for Operations Center
function initAuthorityMap() {
    authMap = L.map('authority-map', {
        zoomControl: true
    }).setView([26.9255, 75.8240], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors | SafeTrail Authority Command'
    }).addTo(authMap);
}

// Poll live telemetry feed
function pollTelemetry(isManual = false) {
    const syncIcon = document.getElementById('sync-icon');
    if (syncIcon && isManual) syncIcon.classList.add('fa-spin');

    fetch('/authority/api/telemetry')
        .then(r => r.json())
        .then(data => {
            currentTelemetry = data;
            document.getElementById('last-sync-time').textContent = `Sync: ${new Date().toLocaleTimeString()}`;
            if (syncIcon && isManual) syncIcon.classList.remove('fa-spin');

            updateStatsCards(data);
            renderMapElements(data);
            renderSOSQueue(data.sos_events);
            renderIncidentQueue(data.incidents);
            updateCharts(data.analytics);

            // Audio Alert if new SOS appears
            const activeSOSCount = data.analytics.active_sos || 0;
            if (activeSOSCount > lastKnownSOSCount && lastKnownSOSCount !== 0) {
                playEmergencyAudioChime();
            }
            lastKnownSOSCount = activeSOSCount;
        })
        .catch(err => {
            console.error("Telemetry error:", err);
            if (syncIcon && isManual) syncIcon.classList.remove('fa-spin');
        });
}

// Update 4 primary telemetry count cards
function updateStatsCards(data) {
    const touristsCount = data.tourists ? data.tourists.length : 0;
    const activeSOS = data.analytics.active_sos || 0;
    const pendingIncidents = data.incidents ? data.incidents.filter(i => i.status !== 'resolved').length : 0;

    document.getElementById('stat-total-tourists').textContent = touristsCount;
    document.getElementById('stat-active-sos').textContent = activeSOS;
    document.getElementById('stat-pending-incidents').textContent = pendingIncidents;

    const sosCard = document.getElementById('card-active-sos');
    const sosDesc = document.getElementById('stat-sos-desc');
    const sosTabCount = document.getElementById('sos-tab-count');
    const incTabCount = document.getElementById('inc-tab-count');

    if (sosTabCount) sosTabCount.textContent = activeSOS;
    if (incTabCount) incTabCount.textContent = pendingIncidents;

    if (activeSOS > 0) {
        sosCard.className = 'bg-rose-50/90 p-4 rounded-2xl border-2 border-rose-500 shadow-lg flex items-center justify-between transition-all animate-pulse';
        sosDesc.textContent = `${activeSOS} Emergency distress signal(s) active!`;
    } else {
        sosCard.className = 'bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between transition-all';
        sosDesc.textContent = 'All sectors quiet and secured.';
    }
}

// Render Zones, POIs, Tourists, and Pulsing SOS Markers on Leaflet
function renderMapElements(data) {
    // 1. Render Zones if not already rendered
    if (zoneLayers.length === 0 && data.zones) {
        data.zones.forEach(zone => {
            const coords = zone.coordinates;
            if (!coords || coords.length === 0) return;

            let color = '#10B981';
            if (zone.risk_level === 'caution') color = '#F59E0B';
            if (zone.risk_level === 'restricted') color = '#EF4444';

            const poly = L.polygon(coords, {
                color: color,
                fillColor: color,
                fillOpacity: 0.2,
                weight: 2
            }).addTo(authMap);

            poly.bindPopup(`
                <div class="text-xs">
                    <span class="font-bold text-[10px] uppercase px-1.5 py-0.5 rounded text-white" style="background:${color}">${zone.risk_level}</span>
                    <div class="font-bold text-slate-900 mt-1">${zone.name}</div>
                    <div class="text-slate-500 text-[11px]">${zone.description}</div>
                </div>
            `);
            zoneLayers.push(poly);
        });
    }

    // 2. Render POIs if not already rendered
    if (!authMap._poisRendered && data.pois) {
        data.pois.forEach(poi => {
            let emoji = '🏥';
            if (poi.type === 'police') emoji = '👮';
            if (poi.type === 'embassy') emoji = '🏛️';

            const icon = L.divIcon({
                className: 'custom-poi-marker',
                html: `<div style="background:#fff; border:1px solid #94a3b8; border-radius:8px; padding:3px; font-size:13px;">${emoji}</div>`,
                iconSize: [26, 26],
                iconAnchor: [13, 13]
            });

            L.marker([poi.lat, poi.lng], { icon: icon }).addTo(authMap)
                .bindPopup(`<strong class="text-xs">${poi.name}</strong><br><span class="text-[11px] text-slate-500">${poi.address}</span>`);
        });
        authMap._poisRendered = true;
    }

    // 3. Render / Update Tourist Markers
    if (data.tourists) {
        data.tourists.forEach(t => {
            if (t.lat && t.lng) {
                // If tourist has active SOS, render high-visibility pulsing beacon
                if (t.has_active_sos) {
                    if (touristMarkers[t.id]) {
                        authMap.removeLayer(touristMarkers[t.id]);
                        delete touristMarkers[t.id];
                    }

                    if (!sosMarkers[t.id]) {
                        const sosIcon = L.divIcon({
                            className: 'custom-sos-container',
                            html: `<div class="custom-sos-marker" style="background:#ef4444; width:22px; height:22px; border-radius:50%; border:3px solid #ffffff; display:flex; align-items:center; justify-content:center; color:#fff; font-size:10px; font-weight:bold;">🚨</div>`,
                            iconSize: [24, 24],
                            iconAnchor: [12, 12]
                        });
                        const m = L.marker([t.lat, t.lng], { icon: sosIcon, zIndexOffset: 1000 }).addTo(authMap);
                        m.bindPopup(buildTouristPopupHtml(t, true));
                        sosMarkers[t.id] = m;
                    } else {
                        sosMarkers[t.id].setLatLng([t.lat, t.lng]);
                    }
                } else {
                    // Remove SOS beacon if resolved
                    if (sosMarkers[t.id]) {
                        authMap.removeLayer(sosMarkers[t.id]);
                        delete sosMarkers[t.id];
                    }

                    if (!touristMarkers[t.id]) {
                        const normalIcon = L.divIcon({
                            className: 'normal-tourist-container',
                            html: `<div style="background:${t.risk_color}; width:16px; height:16px; border-radius:50%; border:2px solid #ffffff; box-shadow:0 0 6px rgba(0,0,0,0.3);"></div>`,
                            iconSize: [16, 16],
                            iconAnchor: [8, 8]
                        });
                        const m = L.marker([t.lat, t.lng], { icon: normalIcon }).addTo(authMap);
                        m.bindPopup(buildTouristPopupHtml(t, false));
                        touristMarkers[t.id] = m;
                    } else {
                        touristMarkers[t.id].setLatLng([t.lat, t.lng]);
                    }
                }
            }
        });
    }
}

function buildTouristPopupHtml(t, isSOS) {
    return `
        <div class="text-xs p-1 min-w-[180px]">
            <div class="flex items-center justify-between pb-1 border-b border-slate-200">
                <span class="font-bold text-slate-900">${t.name}</span>
                <span class="font-mono text-[10px] text-indigo-600 font-bold">${t.digital_id}</span>
            </div>
            <div class="mt-1 text-slate-600 text-[11px]">
                <div>Nationality: <strong>${t.nationality}</strong></div>
                <div>Sector: <strong>${t.zone_name}</strong></div>
                <div>Safety Score: <span style="color:${t.risk_color}; font-weight:bold;">${t.risk_score}/100 (${t.risk_level})</span></div>
            </div>
            ${isSOS ? `<div class="mt-2 p-1.5 bg-rose-600 text-white rounded text-center font-bold text-[10px] uppercase animate-pulse">ACTIVE SOS EMERGENCY</div>` : ''}
            <button onclick="inspectTourist(${t.id})" class="mt-2 w-full py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-[10px] font-bold transition">
                Inspect Medical Snapshot
            </button>
        </div>
    `;
}

// Render SOS Queue Cards in the right tab
function renderSOSQueue(sosEvents) {
    const container = document.getElementById('sos-events-container');
    if (!container) return;

    if (!sosEvents || sosEvents.length === 0) {
        container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">No SOS emergency events reported. All tourists safe.</div>`;
        return;
    }

    container.innerHTML = sosEvents.map(sos => {
        const isResolved = sos.status === 'resolved';
        const cardBg = isResolved ? 'bg-slate-50 border-slate-200 opacity-70' : 'bg-rose-50/70 border-rose-300 shadow-sm';
        const badgeBg = isResolved ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-600 text-white animate-pulse';

        return `
            <div class="p-3.5 rounded-2xl border ${cardBg} space-y-2 text-xs transition-all">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="font-black text-slate-900 text-sm">${sos.tourist_name}</span>
                        <span class="text-[10px] font-mono text-slate-500 font-semibold">(${sos.digital_id_code})</span>
                    </div>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${badgeBg}">
                        ${sos.status}
                    </span>
                </div>

                <div class="grid grid-cols-2 gap-1 text-[11px] text-slate-600">
                    <div>Blood: <strong class="text-rose-700">${sos.blood_group}</strong></div>
                    <div>Allergies: <strong class="text-slate-800">${sos.allergies || 'None'}</strong></div>
                    <div class="col-span-2">Contact: <strong>${sos.emergency_contact_name}</strong> (${sos.emergency_contact_phone})</div>
                </div>

                ${sos.voice_note_text ? `
                <div class="p-2 bg-white rounded-xl border border-rose-200 text-[11px] text-rose-900">
                    <i class="fa-solid fa-comment-dots text-rose-500 mr-1"></i> "${sos.voice_note_text}"
                </div>` : ''}

                <div class="pt-1 flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-200/60">
                    <span>GPS: ${sos.lat.toFixed(4)}, ${sos.lng.toFixed(4)} • ${sos.timestamp.split(' ')[1]}</span>
                </div>

                <div class="flex gap-2 pt-1">
                    <button onclick="inspectTourist(${sos.tourist_id})" class="flex-1 py-1.5 bg-white hover:bg-slate-100 text-slate-800 rounded-xl border border-slate-300 font-bold text-[11px] transition">
                        Full Snapshot
                    </button>
                    ${!isResolved ? `
                    <button onclick="openSOSActionModal(${sos.id}, '${sos.status}')" class="flex-1 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold text-[11px] transition shadow-xs">
                        Dispatch / Resolve
                    </button>` : `
                    <span class="flex-1 text-center py-1 text-[11px] font-bold text-emerald-600">
                        <i class="fa-solid fa-check mr-1"></i> Resolved
                    </span>`}
                </div>
            </div>
        `;
    }).join('');
}

// Render Incident Queue Cards in the incidents tab
function renderIncidentQueue(incidents) {
    const container = document.getElementById('incidents-container');
    if (!container) return;

    const filter = document.getElementById('incident-filter').value;
    let list = incidents || [];
    if (filter !== 'all') {
        list = list.filter(i => i.status === filter);
    }

    if (list.length === 0) {
        container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">No incidents match the selected filter.</div>`;
        return;
    }

    container.innerHTML = list.map(inc => {
        let badgeBg = 'bg-sky-100 text-sky-800';
        if (inc.status === 'under_review') badgeBg = 'bg-amber-100 text-amber-800';
        if (inc.status === 'resolved') badgeBg = 'bg-emerald-100 text-emerald-800';

        return `
            <div class="p-3.5 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-1.5 text-xs">
                <div class="flex items-center justify-between">
                    <span class="font-bold uppercase text-[10px] px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono">
                        ${inc.type}
                    </span>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${badgeBg}">
                        ${inc.status}
                    </span>
                </div>
                <div class="font-bold text-slate-900">${inc.title}</div>
                <p class="text-slate-600 text-[11px] leading-relaxed">${inc.description}</p>
                <div class="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-slate-200">
                    <span>Reporter: ${inc.reporter_name}</span>
                    <span>${inc.timestamp.split(' ')[1]}</span>
                </div>
                ${inc.authority_notes ? `<div class="text-[10px] text-indigo-800 bg-indigo-50 p-1.5 rounded-lg"><strong>Notes:</strong> ${inc.authority_notes}</div>` : ''}
                <div class="flex gap-1.5 pt-1">
                    <button onclick="updateIncidentQuickStatus(${inc.id}, 'under_review')" class="px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 text-[10px] font-bold rounded-lg transition">Under Review</button>
                    <button onclick="updateIncidentQuickStatus(${inc.id}, 'resolved')" class="px-2 py-1 bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-[10px] font-bold rounded-lg transition">Resolve</button>
                </div>
            </div>
        `;
    }).join('');
}

function filterIncidents(val) {
    renderIncidentQueue(currentTelemetry.incidents);
}

// Right Tab Switcher
function switchTab(tab) {
    const tabs = ['sos', 'incidents', 'lookup'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const content = document.getElementById(`tab-content-${t}`);
        if (t === tab) {
            btn.className = 'flex-1 py-2 rounded-xl bg-white text-indigo-600 shadow-xs transition flex items-center justify-center gap-1.5';
            if (t === 'sos') btn.className = 'flex-1 py-2 rounded-xl bg-white text-rose-600 shadow-xs transition flex items-center justify-center gap-1.5';
            content.classList.remove('hidden');
        } else {
            btn.className = 'flex-1 py-2 rounded-xl text-slate-600 hover:text-slate-900 transition flex items-center justify-center gap-1.5';
            content.classList.add('hidden');
        }
    });
}

// Tourist Lookup & Verification
function performTouristLookup() {
    const query = document.getElementById('lookup-input').value.trim();
    if (!query) return;

    fetch(`/authority/api/lookup?q=${encodeURIComponent(query)}`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('lookup-results-container');
            if (!data.results || data.results.length === 0) {
                container.innerHTML = `<div class="p-6 text-center text-slate-400 text-xs">No registered tourists found matching "${query}".</div>`;
                return;
            }

            container.innerHTML = data.results.map(t => `
                <div class="p-3 bg-slate-50 rounded-2xl border border-slate-200 flex items-center justify-between text-xs">
                    <div>
                        <div class="font-bold text-slate-900">${t.name}</div>
                        <div class="text-[11px] font-mono text-indigo-600 font-bold">${t.digital_id}</div>
                        <div class="text-[10px] text-slate-500">${t.nationality} • Masked ID: ${t.masked_id} • Blood: ${t.blood_group}</div>
                    </div>
                    <button onclick="inspectTourist(${t.user_id})" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition">
                        Full Vitals
                    </button>
                </div>
            `).join('');
        });
}

// Inspect Full Tourist Medical Snapshot Modal
function inspectTourist(touristId) {
    fetch(`/authority/api/tourist/${touristId}`)
        .then(r => r.json())
        .then(data => {
            const u = data.user;
            const p = data.profile;
            const risk = data.risk;
            const zone = data.current_zone;

            document.getElementById('modal-name').textContent = u.name;
            document.getElementById('modal-digital-id').textContent = p.digital_id_code || 'ST-2026-REG';
            document.getElementById('modal-nationality').textContent = p.nationality || 'Unknown';
            document.getElementById('modal-photo').src = p.photo_url || '/static/img/default-avatar.png';

            document.getElementById('modal-blood').textContent = p.blood_group || 'Unknown';
            document.getElementById('modal-passport').textContent = p.id_number || 'N/A'; // Authorized view shows full passport!
            document.getElementById('modal-allergies').textContent = p.allergies || 'None reported';
            document.getElementById('modal-conditions').textContent = p.medical_conditions || 'None reported';
            document.getElementById('modal-emergency-contact').textContent = `${p.emergency_contact_name || 'N/A'} (${p.emergency_contact_relation || 'Contact'}) • ${p.emergency_contact_phone || 'N/A'}`;
            document.getElementById('modal-accommodation').textContent = p.accommodation_address || 'Jaipur Local Hotel';

            document.getElementById('modal-zone').textContent = zone ? zone.name : 'Unzoned Territory';
            const riskBadge = document.getElementById('modal-risk-badge');
            riskBadge.textContent = `${risk.level} (${risk.score}/100)`;
            riskBadge.className = `px-2 py-0.5 rounded-full font-bold ${risk.badge_class}`;

            document.getElementById('tourist-modal').classList.remove('hidden');
        });
}

function closeTouristModal() {
    document.getElementById('tourist-modal').classList.add('hidden');
}

// SOS Dispatch & Status Management
function openSOSActionModal(sosId, currentStatus) {
    document.getElementById('action-sos-id').value = sosId;
    document.getElementById('action-sos-status').value = currentStatus === 'active' ? 'acknowledged' : (currentStatus === 'acknowledged' ? 'dispatched' : 'resolved');
    document.getElementById('action-sos-notes').value = '';
    document.getElementById('sos-action-modal').classList.remove('hidden');
}

function closeSOSActionModal() {
    document.getElementById('sos-action-modal').classList.add('hidden');
}

function submitSOSAction() {
    const sosId = document.getElementById('action-sos-id').value;
    const status = document.getElementById('action-sos-status').value;
    const notes = document.getElementById('action-sos-notes').value.trim();

    fetch(`/authority/api/sos/${sosId}/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, notes })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            closeSOSActionModal();
            pollTelemetry(true);
        }
    });
}

function updateIncidentQuickStatus(incidentId, status) {
    const notes = prompt(`Enter authority resolution notes for incident #${incidentId}:`, "Reviewed and logged by Operations Command.");
    if (notes === null) return;

    fetch(`/authority/api/incident/${incidentId}/update-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, authority_notes: notes })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            pollTelemetry(true);
        }
    });
}

// Web Audio API Emergency Siren (Zero External Files needed!)
function playEmergencyAudioChime() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(800, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(400, audioCtx.currentTime + 0.4);

        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);

        osc.start();
        osc.stop(audioCtx.currentTime + 0.45);
    } catch(e) {
        console.log("Audio alert suppressed");
    }
}

// Initialize Analytics Charts (Chart.js)
function initCharts() {
    const ctxType = document.getElementById('chart-incident-types');
    const ctxZone = document.getElementById('chart-zone-density');

    if (ctxType) {
        incidentTypeChart = new Chart(ctxType, {
            type: 'doughnut',
            data: {
                labels: ['Theft', 'Scam', 'Harassment', 'Hazard', 'Other'],
                datasets: [{
                    data: [1, 1, 0, 1, 0],
                    backgroundColor: ['#f43f5e', '#f59e0b', '#8b5cf6', '#0284c7', '#64748b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } }
                }
            }
        });
    }

    if (ctxZone) {
        zoneDensityChart = new Chart(ctxZone, {
            type: 'bar',
            data: {
                labels: ['City Palace', 'Johari Bazaar', 'Nahargarh Pass'],
                datasets: [{
                    label: 'Reported Incidents',
                    data: [1, 2, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 10 } } },
                    x: { ticks: { font: { size: 10 } } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

// Update charts with live telemetry metrics
function updateCharts(analytics) {
    if (!analytics) return;

    if (incidentTypeChart && analytics.incident_types) {
        incidentTypeChart.data.labels = Object.keys(analytics.incident_types);
        incidentTypeChart.data.datasets[0].data = Object.values(analytics.incident_types);
        incidentTypeChart.update();
    }

    if (zoneDensityChart && analytics.zone_incidents) {
        zoneDensityChart.data.labels = Object.keys(analytics.zone_incidents);
        zoneDensityChart.data.datasets[0].data = Object.values(analytics.zone_incidents);
        zoneDensityChart.update();
    }
}
