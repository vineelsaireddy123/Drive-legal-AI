/* DriveLegal.ai - Client v2.0 */

const API = '';
let MAP = null;
let MAP_READY = false;
let CURRENT_PANEL = 'chat';
let THEME = localStorage.getItem('dl_theme') || 'dark';
let MAP_TILE_LAYER = null;
let GEO_DETECTED_COUNTRY = null;

const TILE_DARK = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const TILE_LIGHT = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

// Translation dictionary will be loaded here
let i18n = {};
let currentLang = 'en';

function $(id) { return document.getElementById(id); }

/* Navigation */
function go(panel) {
  document.querySelectorAll('.panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  const target = $('p-' + panel);
  if (target) target.classList.add('active');

  const navBtn = document.querySelector('.nav-item[data-panel="' + panel + '"]');
  if (navBtn) navBtn.classList.add('active');

  CURRENT_PANEL = panel;

  // Close mobile sidebar if open
  document.body.classList.remove('sidebar-open');

  // Update header title
  const title = navBtn ? navBtn.querySelector('.sidebar-text').innerText : 'DriveLegal.ai';
  $('h-title').innerText = title;

  // Init map if needed
  if (panel === 'map' && !MAP_READY) setTimeout(initMap, 100);
  if (panel === 'map' && MAP) setTimeout(() => MAP.invalidateSize(), 200);

  // Load data if needed
  if (panel === 'calculator') loadCalcData();
  if (panel === 'dashboard') loadDashboard();
  if (panel === 'rules') initRulesPanel();
}

/* UI interactions */
document.addEventListener('DOMContentLoaded', () => {
  // Theme initialization
  if (THEME === 'light') {
    document.body.classList.add('light-theme');
  }

  // Event listeners
  $('btn-theme').addEventListener('click', toggleTheme);
  $('btn-menu').addEventListener('click', () => document.body.classList.add('sidebar-open'));
  $('btn-close-sidebar').addEventListener('click', () => document.body.classList.remove('sidebar-open'));

  // Chat input
  $('btn-send').addEventListener('click', () => {
    const input = $('chat-input');
    if (input.value.trim()) {
      sendChat(input.value.trim());
      input.value = '';
    }
  });

  $('chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const input = $('chat-input');
      if (input.value.trim()) {
        sendChat(input.value.trim());
        input.value = '';
      }
    }
  });

  // Calculator
  $('btn-calculate').addEventListener('click', calculateFine);

  // Auth Modal
  $('btn-auth-action').addEventListener('click', () => {
    $('auth-modal').classList.add('active');
  });

  $('btn-auth-toggle').addEventListener('click', () => {
    const isLogin = $('auth-title').innerText === 'Sign In';
    $('auth-title').innerText = isLogin ? 'Create Account' : 'Sign In';
    $('btn-auth-submit').innerText = isLogin ? 'Create Account' : 'Sign In';
    $('btn-auth-toggle').innerText = isLogin ? 'Already have an account? Sign in' : "Don't have an account? Create one";
    document.querySelector('.auth-register-only').style.display = isLogin ? 'block' : 'none';
  });

  // Emergency
  $('btn-sos').addEventListener('click', activateSOS);

  // Logout
  $('btn-logout').addEventListener('click', handleLogout);

  // Load data
  loadTranslations();
  preloadOfflineData();
  checkAuth();
  showLoginGate();
  autoDetectCountry();

  // PWA setup
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(console.error);
  }
});

/* Theme */
function toggleTheme() {
  THEME = THEME === 'dark' ? 'light' : 'dark';
  if (THEME === 'light') {
    document.body.classList.add('light-theme');
  } else {
    document.body.classList.remove('light-theme');
  }
  localStorage.setItem('dl_theme', THEME);
  updateMapTiles();
  showToast(THEME === 'dark' ? 'Switched to dark mode' : 'Switched to light mode');
}

/* Map initialization */
function initMap() {
  if (MAP_READY || typeof L === 'undefined') return;
  MAP_READY = true;

  MAP = L.map('map-view', {
    zoomControl: false, attributionControl: false,
    zoomAnimation: true, markerZoomAnimation: true
  }).setView([20.5937, 78.9629], 5);

  MAP_TILE_LAYER = L.tileLayer(THEME === 'light' ? TILE_LIGHT : TILE_DARK, {
    maxZoom: 19, subdomains: 'abcd'
  }).addTo(MAP);

  L.control.zoom({ position: 'bottomleft' }).addTo(MAP);

  // Auto-locate
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        MAP.setView([pos.coords.latitude, pos.coords.longitude], 13);
        L.marker([pos.coords.latitude, pos.coords.longitude]).addTo(MAP)
          .bindPopup("You are here").openPopup();
      },
      () => { }
    );
  }

  // Load hazards
  fetch(API + '/api/hazards')
    .then(r => r.json())
    .then(data => {
      if (Array.isArray(data)) {
        data.forEach(h => {
          L.circleMarker([h.lat, h.lng], {
            color: h.type === 'accident' ? 'red' : 'orange',
            radius: 8,
            fillOpacity: 0.7
          }).addTo(MAP).bindPopup(`<b>${h.type.toUpperCase()}</b><br>${h.description}`);
        });
      }
    }).catch(e => console.log('Offline: cannot load map hazards'));

  // Locate button handler
  $('btn-locate').addEventListener('click', () => {
    if (!navigator.geolocation) {
      showToast('Geolocation not supported', 'error');
      return;
    }
    showToast('Finding your location...');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        MAP.setView([pos.coords.latitude, pos.coords.longitude], 15);
        L.marker([pos.coords.latitude, pos.coords.longitude]).addTo(MAP)
          .bindPopup('📍 You are here').openPopup();
        showToast('Location found!', 'success');
      },
      (err) => {
        showToast('Could not get location. Enable GPS and allow permissions.', 'error');
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  });

  // Map search functionality
  $('map-search').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const query = $('map-search').value.trim();
      if (!query) return;
      fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`)
        .then(r => r.json())
        .then(results => {
          if (results.length > 0) {
            const r = results[0];
            MAP.setView([parseFloat(r.lat), parseFloat(r.lon)], 14);
            L.marker([parseFloat(r.lat), parseFloat(r.lon)]).addTo(MAP)
              .bindPopup(`<b>${r.display_name}</b>`).openPopup();
          } else {
            showToast('Location not found', 'error');
          }
        }).catch(() => showToast('Search failed. Check connection.', 'error'));
    }
  });
}

function updateMapTiles() {
  if (!MAP || !MAP_TILE_LAYER) return;
  MAP.removeLayer(MAP_TILE_LAYER);
  MAP_TILE_LAYER = L.tileLayer(THEME === 'light' ? TILE_LIGHT : TILE_DARK, {
    maxZoom: 19, subdomains: 'abcd'
  }).addTo(MAP);
}

/* Chat */
function appendMessage(text, isUser = false) {
  const msgs = $('chat-msgs');
  const div = document.createElement('div');
  div.className = `message ${isUser ? 'user' : 'ai'}`;

  // Convert basic markdown (bold)
  let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Format lists
  formattedText = formattedText.replace(/â€¢ (.*?)(?=\n|$)/g, '<li>$1</li>');
  if (formattedText.includes('<li>')) formattedText = `<ul>${formattedText}</ul>`;
  // Format newlines
  formattedText = formattedText.replace(/\n/g, '<br>');

  div.innerHTML = `<div class="msg-bubble">${formattedText}</div>`;

  // Remove suggestion chips if they exist
  const chips = $('chat-suggestions');
  if (chips && isUser) chips.style.display = 'none';

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function sendChat(message) {
  appendMessage(message, true);

  // Show typing indicator
  const typingId = 'typing-' + Date.now();
  const msgs = $('chat-msgs');
  const typing = document.createElement('div');
  typing.className = 'message ai typing-indicator';
  typing.id = typingId;
  typing.innerHTML = '<div class="msg-bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
  msgs.appendChild(typing);
  msgs.scrollTop = msgs.scrollHeight;

  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('dl_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const payload = { message: message };
  if (GEO_DETECTED_COUNTRY) payload.country_context = GEO_DETECTED_COUNTRY;

  fetch(API + '/api/chat', {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      $(typingId).remove();
      appendMessage(data.text || 'Sorry, I could not process that request.');
    })
    .catch(err => {
      $(typingId).remove();
      appendMessage('Network error. Operating in offline mode. What is the fine for driving without a helmet?');
      $('offline-badge').style.display = 'flex';
    });
}

/* Calculator */
let CACHED_VIOLATIONS = null;
let CACHED_STATES = null;
let CACHED_COUNTRIES = null;
let CURRENT_COUNTRY = 'india';
let OFFLINE_NATIONAL_DATA = null;
let OFFLINE_STATES_DATA = null;
let OFFLINE_GLOBAL_DATA = null;
let CITY_STATE_MAP = null;
let GEO_DETECTED_STATE = null;

/* Pre-load JSON data for offline calculator */
function preloadOfflineData() {
  fetch('/data/india_national.json').then(r => r.json()).then(d => { OFFLINE_NATIONAL_DATA = d; }).catch(() => { });
  fetch('/data/india_states.json').then(r => r.json()).then(d => { OFFLINE_STATES_DATA = d; CITY_STATE_MAP = d.city_to_state_mapping || {}; }).catch(() => { });
  fetch('/data/global_rules.json').then(r => r.json()).then(d => { OFFLINE_GLOBAL_DATA = d; }).catch(() => { });
}

function loadCalcData() {
  // Load Countries
  if (!CACHED_COUNTRIES) {
    fetch(API + '/api/countries')
      .then(r => r.json())
      .then(data => {
        CACHED_COUNTRIES = data;
        const select = $('calc-country');
        // Avoid duplicating options on re-entry
        if (select.options.length <= 1) {
          Object.keys(data).forEach(key => {
            const opt = document.createElement('option');
            opt.value = key;
            opt.innerText = data[key];
            select.appendChild(opt);
          });
        }
      }).catch(e => {
        // Offline: load from cached global data
        if (OFFLINE_GLOBAL_DATA && OFFLINE_GLOBAL_DATA.countries) {
          CACHED_COUNTRIES = {};
          const select = $('calc-country');
          if (select.options.length <= 1) {
            Object.keys(OFFLINE_GLOBAL_DATA.countries).forEach(key => {
              CACHED_COUNTRIES[key] = OFFLINE_GLOBAL_DATA.countries[key].name;
              const opt = document.createElement('option');
              opt.value = key;
              opt.innerText = OFFLINE_GLOBAL_DATA.countries[key].name;
              select.appendChild(opt);
            });
          }
        }
      });
  }

  // Load States (India only)
  if (!CACHED_STATES) {
    fetch(API + '/api/states')
      .then(r => r.json())
      .then(data => {
        CACHED_STATES = data;
        populateStateSelector(data);
      }).catch(e => {
        // Offline: build from cached states data
        if (OFFLINE_STATES_DATA) {
          CACHED_STATES = {};
          const states = OFFLINE_STATES_DATA.states || {};
          const uts = OFFLINE_STATES_DATA.union_territories || {};
          Object.keys(states).forEach(k => { CACHED_STATES[k] = states[k].name; });
          Object.keys(uts).forEach(k => { CACHED_STATES[k] = uts[k].name; });
          populateStateSelector(CACHED_STATES);
        }
      });
  }

  // Load Violations for current country
  loadViolationsForCountry(CURRENT_COUNTRY);

  // Country change handler (only bind once)
  const countrySelect = $('calc-country');
  if (!countrySelect._bound) {
    countrySelect._bound = true;
    countrySelect.addEventListener('change', (e) => {
      CURRENT_COUNTRY = e.target.value;
      const stateGroup = $('state-group');
      if (CURRENT_COUNTRY === 'india') {
        stateGroup.style.display = 'block';
      } else {
        stateGroup.style.display = 'none';
      }
      CACHED_VIOLATIONS = null;
      loadViolationsForCountry(CURRENT_COUNTRY);
    });
  }

  // Auto-detect state from geolocation (geo-fencing)
  autoDetectState();
}

function populateStateSelector(data) {
  const select = $('calc-state');
  if (select.options.length <= 1) {
    Object.keys(data).forEach(key => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.innerText = data[key];
      select.appendChild(opt);
    });
  }
  // If geo-detected state is set, auto-select it
  if (GEO_DETECTED_STATE && data[GEO_DETECTED_STATE]) {
    select.value = GEO_DETECTED_STATE;
    showToast(`Auto-detected: ${data[GEO_DETECTED_STATE]}`, 'success');
  }
}

function loadViolationsForCountry(country) {
  if (CACHED_VIOLATIONS) return;

  const url = country === 'india' ? API + '/api/violations' : API + '/api/violations?country=' + country;

  fetch(url)
    .then(r => r.json())
    .then(data => {
      CACHED_VIOLATIONS = data;
      renderViolationList(data);
    }).catch(e => {
      // Offline fallback: build from cached JSON
      if (country === 'india' && OFFLINE_NATIONAL_DATA) {
        const v = OFFLINE_NATIONAL_DATA.violations || {};
        CACHED_VIOLATIONS = {};
        Object.keys(v).forEach(k => { CACHED_VIOLATIONS[k] = v[k].name; });
        renderViolationList(CACHED_VIOLATIONS);
      } else if (OFFLINE_GLOBAL_DATA && OFFLINE_GLOBAL_DATA.countries && OFFLINE_GLOBAL_DATA.countries[country]) {
        const v = OFFLINE_GLOBAL_DATA.countries[country].violations || {};
        CACHED_VIOLATIONS = {};
        Object.keys(v).forEach(k => { CACHED_VIOLATIONS[k] = v[k].name; });
        renderViolationList(CACHED_VIOLATIONS);
      }
    });
}

function renderViolationList(data) {
  const list = $('violation-list');
  list.innerHTML = '';
  $('selected-violations').innerHTML = '<span class="placeholder-text">Select at least one violation...</span>';

  Object.keys(data).forEach(key => {
    const item = document.createElement('div');
    item.className = 'violation-item';
    item.innerHTML = `
      <label>
        <input type="checkbox" value="${key}" class="viol-cb">
        <span>${data[key]}</span>
      </label>
    `;
    list.appendChild(item);
  });

  document.querySelectorAll('.viol-cb').forEach(cb => {
    cb.addEventListener('change', updateSelectedViolations);
  });
}

function updateSelectedViolations() {
  const selected = [];
  document.querySelectorAll('.viol-cb:checked').forEach(cb => {
    selected.push(cb.nextElementSibling.innerText);
  });

  const container = $('selected-violations');
  if (selected.length === 0) {
    container.innerHTML = '<span class="placeholder-text">Select at least one violation...</span>';
  } else {
    container.innerHTML = selected.map(v => `<span class="chip">${v}</span>`).join('');
  }
}

function calculateFine() {
  const violations = Array.from(document.querySelectorAll('.viol-cb:checked')).map(cb => cb.value);

  if (violations.length === 0) {
    showToast('Please select at least one violation', 'error');
    return;
  }

  const country = $('calc-country').value;
  const state = $('calc-state').value;
  const vehicle = $('calc-vehicle').value;
  const isRepeat = document.querySelector('input[name="offense_type"]:checked').value === 'repeat';

  // Use different endpoints for India vs global
  let endpoint, payload;

  if (country === 'india') {
    endpoint = API + '/api/calculate';
    payload = {
      violations: violations,
      vehicle_type: vehicle,
      is_repeat: isRepeat
    };
    if (state !== 'national') payload.state = state;
  } else {
    endpoint = API + '/api/calculate/global';
    payload = {
      country: country,
      violations: violations,
      is_repeat: isRepeat
    };
  }

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      displayCalcResults(data);
      saveCalcHistory(data);
    })
    .catch(err => {
      // OFFLINE FALLBACK: Calculate locally from cached JSON data
      console.log('API failed, trying offline calculation:', err.message);
      const offlineResult = calculateFineOffline(violations, country, state, vehicle, isRepeat);
      if (offlineResult) {
        displayCalcResults(offlineResult, true);
      } else {
        showToast('Unable to calculate. Please check your connection.', 'error');
      }
    });
}

function displayCalcResults(data, isOffline = false) {
  const results = $('calc-results');
  const breakdown = $('result-breakdown');
  const currency = data.currency || 'Rs.';

  const offlineBadge = isOffline ? '<span class="offline-calc-badge">⚡ Offline Estimate</span>' : '';

  breakdown.innerHTML = data.violations.map(v => {
    if (v.error) return `<div class="fine-row"><div><strong>${v.error}</strong></div></div>`;
    const section = v.section ? `<div class="text-sm text-muted">Sec ${v.section}</div>` : '';
    const penalties = v.additional_penalties && v.additional_penalties.length > 0
      ? `<div class="text-sm text-muted" style="margin-top:4px;">${v.additional_penalties.join(', ')}</div>` : '';
    return `
      <div class="fine-row">
        <div>
          <strong>${v.violation_name}</strong>
          ${section}
          ${penalties}
        </div>
        <div class="text-right">
          <strong>${currency} ${v.total_fine.toLocaleString()}</strong>
        </div>
      </div>
    `;
  }).join('');

  $('result-total-amt').innerText = `${currency} ${data.grand_total.toLocaleString()}`;

  // Show offline badge if applicable
  const existingBadge = results.querySelector('.offline-calc-badge');
  if (existingBadge) existingBadge.remove();
  if (isOffline) {
    const badge = document.createElement('div');
    badge.className = 'offline-calc-badge';
    badge.innerHTML = '⚡ Offline Estimate — fines may vary by local enforcement';
    results.querySelector('h3').after(badge);
  }

  results.style.display = 'block';
  results.scrollIntoView({ behavior: 'smooth' });
}

/* Offline Calculator — mirrors challan_calculator.py logic */
const VEHICLE_MODIFIERS = {
  two_wheeler: 0.75, auto_rickshaw: 0.85, car: 1.0,
  taxi: 1.1, bus: 1.5, truck: 1.5, commercial: 1.3, e_rickshaw: 0.8
};

function calculateFineOffline(violationKeys, country, stateKey, vehicleType, isRepeat) {
  let sourceData = null;
  let currency = 'Rs.';
  let isIndia = country === 'india';

  if (isIndia) {
    if (!OFFLINE_NATIONAL_DATA) return null;
    sourceData = OFFLINE_NATIONAL_DATA.violations || {};
  } else {
    if (!OFFLINE_GLOBAL_DATA || !OFFLINE_GLOBAL_DATA.countries || !OFFLINE_GLOBAL_DATA.countries[country]) return null;
    const countryData = OFFLINE_GLOBAL_DATA.countries[country];
    sourceData = countryData.violations || {};
    currency = countryData.currency_symbol || '$';
  }

  const results = [];
  let grandTotal = 0;
  const modifier = VEHICLE_MODIFIERS[vehicleType] || 1.0;

  for (const vk of violationKeys) {
    const violation = sourceData[vk];
    if (!violation) {
      results.push({ error: `Unknown violation: ${vk}` });
      continue;
    }

    let fineData = violation.fine || 0;
    let fine = 0;

    if (typeof fineData === 'object') {
      if (isRepeat) {
        fine = fineData.repeat_offense || fineData.first_offense || 0;
      } else {
        fine = fineData.first_offense || 0;
      }
      // Handle nested vehicle-type fines (e.g. overspeeding)
      if (typeof fine === 'object') {
        fine = fine[vehicleType] || fine.default || 0;
      }
    } else {
      fine = fineData;
      if (isRepeat) fine = fine * 2;
    }

    // Apply vehicle modifier (India only)
    if (isIndia) {
      fine = Math.round(fine * modifier);
    }

    // Check state override (India only)
    let stateFine = null;
    let stateLabel = 'National (MV Act 2019)';
    if (isIndia && stateKey && stateKey !== 'national' && OFFLINE_STATES_DATA) {
      const states = OFFLINE_STATES_DATA.states || {};
      const uts = OFFLINE_STATES_DATA.union_territories || {};
      const stateData = states[stateKey] || uts[stateKey];
      if (stateData) {
        stateLabel = stateData.name || stateKey;
        const override = (stateData.overrides || {})[vk];
        if (override) {
          if (isRepeat) {
            stateFine = override.repeat_offense || override.first_offense || fine;
          } else {
            stateFine = override.first_offense || fine;
          }
          if (typeof stateFine === 'object') {
            stateFine = stateFine[vehicleType] || stateFine.default || fine;
          }
          stateFine = Math.round(stateFine * modifier);
        }
      }
    }

    const totalFine = stateFine !== null ? stateFine : fine;
    grandTotal += totalFine;

    results.push({
      violation_key: vk,
      violation_name: violation.name || vk,
      section: violation.section || '',
      total_fine: totalFine,
      is_repeat: isRepeat,
      additional_penalties: violation.additional_penalties || [],
      safety_advice: violation.safety_advice || ''
    });
  }

  return {
    violations: results,
    count: results.length,
    grand_total: grandTotal,
    currency: currency,
    vehicle_type: vehicleType,
    state: stateKey || 'national',
    is_repeat: isRepeat
  };
}

/* Geo-fencing: Auto-detect user state from location */
function autoDetectState() {
  if (GEO_DETECTED_STATE) return; // Already detected
  if (!navigator.geolocation) return;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;

      // Use Nominatim reverse geocoding (free, no API key)
      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&addressdetails=1`)
        .then(r => r.json())
        .then(data => {
          const addr = data.address || {};
          const city = (addr.city || addr.town || addr.village || addr.county || '').toLowerCase();
          const stateFromGeo = (addr.state || '').toLowerCase();

          // Try city mapping first
          if (CITY_STATE_MAP && city && CITY_STATE_MAP[city]) {
            GEO_DETECTED_STATE = CITY_STATE_MAP[city];
          } else {
            // Try matching state name directly
            fetch(API + '/api/geo/state?city=' + encodeURIComponent(city))
              .then(r => r.json())
              .then(d => {
                if (d.state_key) {
                  GEO_DETECTED_STATE = d.state_key;
                  const sel = $('calc-state');
                  if (sel && CACHED_STATES && CACHED_STATES[d.state_key]) {
                    sel.value = d.state_key;
                    showToast(`📍 Detected: ${CACHED_STATES[d.state_key]}`, 'success');
                  }
                }
              }).catch(() => { });
            return;
          }

          // Auto-select detected state
          if (GEO_DETECTED_STATE) {
            const sel = $('calc-state');
            if (sel && CACHED_STATES && CACHED_STATES[GEO_DETECTED_STATE]) {
              sel.value = GEO_DETECTED_STATE;
              showToast(`📍 Detected: ${CACHED_STATES[GEO_DETECTED_STATE]}`, 'success');
            }
          }
        }).catch(() => { }); // Silently fail if geocoding unavailable
    },
    () => { } // Silently fail if geolocation denied
  );
}

/* Auto-detect user's country from geolocation */
function autoDetectCountry() {
  if (GEO_DETECTED_COUNTRY) return;
  if (!navigator.geolocation) return;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;

      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&addressdetails=1`)
        .then(r => r.json())
        .then(data => {
          const countryCode = (data.address?.country_code || '').toLowerCase();
          const countryName = data.address?.country || '';

          // Map country codes to our keys
          const countryMap = {
            'in': 'india', 'us': 'usa', 'gb': 'uk', 'ae': 'uae',
            'de': 'germany', 'au': 'australia', 'ca': 'canada'
          };

          GEO_DETECTED_COUNTRY = countryMap[countryCode] || countryCode;

          if (GEO_DETECTED_COUNTRY && countryName) {
            showToast(`📍 Detected: ${countryName}`, 'success');
          }
        }).catch(() => { });
    },
    () => { },
    { enableHighAccuracy: false, timeout: 10000 }
  );
}


/* Dashboard & Auth */
function showLoginGate() {
  const token = localStorage.getItem('dl_token');
  const gate = $('login-gate');
  if (!gate) return;

  if (token) {
    gate.style.display = 'none';
  } else {
    // Show gate after a small delay (let page render first)
    setTimeout(() => { gate.style.display = 'flex'; }, 300);
  }
}

function dismissLoginGate() {
  const gate = $('login-gate');
  if (gate) {
    gate.style.opacity = '0';
    setTimeout(() => { gate.style.display = 'none'; }, 300);
  }
}

function checkAuth() {
  const token = localStorage.getItem('dl_token');
  const userStr = localStorage.getItem('dl_user');

  if (token && userStr) {
    const user = JSON.parse(userStr);
    const name = user.full_name || user.email;
    $('display-name').innerText = name;
    $('display-action').innerText = 'Signed In';
    $('user-avatar').innerText = name.charAt(0).toUpperCase();
    $('btn-auth-action').innerText = 'Account';
    $('btn-logout').style.display = 'flex';
    $('dash-auth-required').style.display = 'none';
    $('dash-content').style.display = 'block';
    // Dismiss login gate if open
    const gate = $('login-gate');
    if (gate) gate.style.display = 'none';
  } else {
    $('display-name').innerText = 'Guest';
    $('display-action').innerText = 'Tap to sign in';
    $('user-avatar').innerText = 'G';
    $('btn-auth-action').innerText = 'Sign In';
    $('btn-logout').style.display = 'none';
    $('dash-auth-required').style.display = 'flex';
    $('dash-content').style.display = 'none';
  }
}

function handleLogout() {
  localStorage.removeItem('dl_token');
  localStorage.removeItem('dl_user');
  checkAuth();
  showToast('Signed out successfully');
  go('chat');
  showLoginGate();
}

function handleAuth() {
  const isLogin = $('auth-title').innerText === 'Sign In';
  const email = $('auth-email').value;
  const password = $('auth-password').value;
  const name = $('auth-name').value;

  const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register';
  const payload = { email, password };
  if (!isLogin) payload.full_name = name;

  fetch(API + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);

      if (isLogin) {
        localStorage.setItem('dl_token', data.token);
        localStorage.setItem('dl_user', JSON.stringify(data.user));
        $('auth-modal').classList.remove('active');
        checkAuth();
        showToast('Signed in successfully');
        if (CURRENT_PANEL === 'dashboard') loadDashboard();
      } else {
        showToast('Account created! Please sign in.');
        $('btn-auth-toggle').click(); // Switch to login
      }
    })
    .catch(err => {
      showToast(err.message, 'error');
    });
}

function loadDashboard() {
  const token = localStorage.getItem('dl_token');
  if (!token) return;

  fetch(API + '/api/user/dashboard', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
    .then(r => r.json())
    .then(data => {
      if (data.stats) {
        $('stat-queries').innerText = data.stats.queries || 0;
        $('stat-reports').innerText = data.stats.reports || 0;

        const score = data.user.safety_score || 100;
        $('score-val').innerText = score;

        // Update ring
        const circle = $('score-progress');
        const radius = circle.r.baseVal.value;
        const circumference = radius * 2 * Math.PI;
        const offset = circumference - (score / 100) * circumference;

        circle.style.strokeDashoffset = offset;

        if (score >= 90) circle.style.stroke = '#22c55e'; // Green
        else if (score >= 70) circle.style.stroke = '#eab308'; // Yellow
        else circle.style.stroke = '#ef4444'; // Red
      }
    })
    .catch(e => console.log('Dashboard data load failed'));
}

/* Save calculator results per user */
function saveCalcHistory(data) {
  const token = localStorage.getItem('dl_token');
  if (!token) return;

  fetch(API + '/api/user/calculator-history', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      country: $('calc-country').value,
      state: $('calc-state').value,
      vehicle_type: $('calc-vehicle').value,
      violations: data.violations.map(v => v.violation_name),
      grand_total: data.grand_total,
      currency: data.currency || 'Rs.',
      is_repeat: data.is_repeat
    })
  }).catch(() => { });
}

/* Traffic Rules Browser */
let RULES_LOADED_COUNTRY = null;

function initRulesPanel() {
  const select = $('rules-country');
  if (!select._bound) {
    select._bound = true;
    select.addEventListener('change', (e) => {
      loadRulesForDisplay(e.target.value);
    });
  }
  // Auto-set country from geo detection
  if (GEO_DETECTED_COUNTRY) {
    select.value = GEO_DETECTED_COUNTRY;
  }
  loadRulesForDisplay(select.value);
}

function loadRulesForDisplay(country) {
  if (RULES_LOADED_COUNTRY === country) return;

  const content = $('rules-content');
  content.innerHTML = '<div class="empty-state">Loading rules...</div>';

  fetch(API + '/api/rules/' + country)
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      RULES_LOADED_COUNTRY = country;
      renderRules(data);
    })
    .catch(err => {
      // Offline fallback from preloaded data
      if (country === 'india' && OFFLINE_NATIONAL_DATA) {
        renderRules({
          name: 'India', drive_side: 'left', speed_unit: 'km/h',
          bac_limit: '0.03%', emergency_number: '112 / 100 / 108',
          legal_driving_age: 18, currency_symbol: 'Rs.',
          general_rules: OFFLINE_NATIONAL_DATA.general_rules || {},
          violations: OFFLINE_NATIONAL_DATA.violations || {}
        });
      } else if (OFFLINE_GLOBAL_DATA?.countries?.[country]) {
        renderRules(OFFLINE_GLOBAL_DATA.countries[country]);
      } else {
        content.innerHTML = '<div class="empty-state">Could not load rules. Check your connection.</div>';
      }
    });
}

function renderRules(data) {
  const content = $('rules-content');
  const currency = data.currency_symbol || '$';
  const generalRules = data.general_rules || {};
  const violations = data.violations || {};

  let html = `
    <div class="rules-info-grid">
      <div class="rules-info-card">
        <div class="rules-info-icon">🚗</div>
        <div class="rules-info-label">Drive Side</div>
        <div class="rules-info-value">${(data.drive_side || 'right').toUpperCase()}</div>
      </div>
      <div class="rules-info-card">
        <div class="rules-info-icon">⚡</div>
        <div class="rules-info-label">Speed Unit</div>
        <div class="rules-info-value">${data.speed_unit || 'km/h'}</div>
      </div>
      <div class="rules-info-card">
        <div class="rules-info-icon">🍺</div>
        <div class="rules-info-label">BAC Limit</div>
        <div class="rules-info-value">${data.bac_limit || 'Varies'}</div>
      </div>
      <div class="rules-info-card">
        <div class="rules-info-icon">🎂</div>
        <div class="rules-info-label">Legal Driving Age</div>
        <div class="rules-info-value">${data.legal_driving_age || '18'}</div>
      </div>
      <div class="rules-info-card">
        <div class="rules-info-icon">🚨</div>
        <div class="rules-info-label">Emergency</div>
        <div class="rules-info-value">${data.emergency_number || '112'}</div>
      </div>
    </div>
  `;

  // Speed limits
  if (generalRules.speed_limits) {
    html += '<h3 class="rules-section-title">Speed Limits</h3><div class="rules-speed-grid">';
    for (const [road, limit] of Object.entries(generalRules.speed_limits)) {
      const label = road.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      html += `<div class="rules-speed-card"><span class="speed-road">${label}</span><span class="speed-limit">${limit}</span></div>`;
    }
    html += '</div>';
  }

  // Documents required  
  if (generalRules.documents_required) {
    html += '<h3 class="rules-section-title">Required Documents</h3><div class="rules-docs-list">';
    generalRules.documents_required.forEach(doc => {
      html += `<div class="rules-doc-item">📄 ${doc}</div>`;
    });
    html += '</div>';
  }

  // License requirements
  if (generalRules.license_requirements) {
    html += `<h3 class="rules-section-title">License Requirements</h3><p class="rules-text">${generalRules.license_requirements}</p>`;
  }

  // Violations
  const violKeys = Object.keys(violations);
  if (violKeys.length > 0) {
    html += '<h3 class="rules-section-title">Violations & Fines</h3>';
    violKeys.forEach(key => {
      const v = violations[key];
      const fine = v.fine || {};
      const firstFine = typeof fine === 'object' ? fine.first_offense : fine;
      const repeatFine = typeof fine === 'object' ? fine.repeat_offense : fine;
      const penalties = (v.additional_penalties || []).join(', ');

      html += `
        <div class="rules-violation-card">
          <div class="rv-header">
            <span class="rv-name">${v.name || key}</span>
            <span class="rv-fine">${currency} ${(firstFine || 0).toLocaleString()}</span>
          </div>
          ${v.section ? `<div class="rv-section">Section ${v.section}</div>` : ''}
          <div class="rv-desc">${v.description || ''}</div>
          ${repeatFine && repeatFine !== firstFine ? `<div class="rv-repeat">Repeat offense: ${currency} ${repeatFine.toLocaleString()}</div>` : ''}
          ${penalties ? `<div class="rv-penalties">${penalties}</div>` : ''}
          ${v.safety_advice ? `<div class="rv-advice">💡 ${v.safety_advice}</div>` : ''}
        </div>
      `;
    });
  }

  content.innerHTML = html;
}

/* Emergency */
function activateSOS() {
  const btn = $('btn-sos');
  btn.classList.add('active');
  btn.innerText = 'LOCATING...';

  showToast('Activating SOS protocol...');

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const mapsLink = `https://maps.google.com/?q=${lat},${lng}`;

        btn.innerText = 'SOS SENT';
        btn.style.backgroundColor = '#ef4444';

        // Show share sheet natively if possible
        if (navigator.share) {
          navigator.share({
            title: 'EMERGENCY: I need help',
            text: `I'm in an emergency. My location: ${mapsLink}`,
            url: mapsLink
          }).catch(console.error);
        } else {
          // Fallback
          showToast(`SOS Ready! Location: ${lat.toFixed(4)}, ${lng.toFixed(4)}`, 'error');
          setTimeout(() => {
            btn.innerText = 'SOS';
            btn.classList.remove('active');
          }, 5000);
        }
      },
      (err) => {
        btn.innerText = 'GPS FAILED';
        showToast('Could not get GPS location', 'error');
        setTimeout(() => {
          btn.innerText = 'SOS';
          btn.classList.remove('active');
        }, 3000);
      }
    );
  } else {
    showToast('GPS not supported on this device', 'error');
  }
}

/* Utilities */
function showToast(msg, type = 'success') {
  const wrap = $('toasts');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerText = msg;
  wrap.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function loadTranslations() {
  fetch('/data/translations.json')
    .then(r => r.json())
    .then(data => {
      i18n = data;
      // Setup language selector
      $('lang-select').addEventListener('change', (e) => {
        currentLang = e.target.value;
        applyTranslations();
      });
    })
    .catch(e => console.log('Could not load translations'));
}

function applyTranslations() {
  if (!i18n[currentLang]) return;
  const dict = i18n[currentLang];

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) {
      if (el.tagName === 'INPUT' && el.type === 'text') {
        el.placeholder = dict[key];
      } else {
        el.innerText = dict[key];
      }
    }
  });
}

/* Network Status Detection */
window.addEventListener('online', () => {
  $('offline-badge').style.display = 'none';
  showToast('Back online!', 'success');
});

window.addEventListener('offline', () => {
  $('offline-badge').style.display = 'flex';
  showToast('You are offline. Some features may be limited.', 'warning');
});

// Check initial state
if (!navigator.onLine) {
  document.addEventListener('DOMContentLoaded', () => {
    $('offline-badge').style.display = 'flex';
  });
}

/* Voice Input (Web Speech API) */
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  document.addEventListener('DOMContentLoaded', () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    $('btn-voice').addEventListener('click', () => {
      $('btn-voice').classList.add('active');
      recognition.start();
      showToast('Listening... Speak now');
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      $('chat-input').value = transcript;
      $('btn-voice').classList.remove('active');
    };

    recognition.onerror = () => {
      $('btn-voice').classList.remove('active');
      showToast('Voice input failed. Try again.', 'error');
    };

    recognition.onend = () => {
      $('btn-voice').classList.remove('active');
    };
  });
}


