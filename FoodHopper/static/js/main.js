(function () {
  let map;
  let markersLayer;
  let routingControl = null;
  let selectedPlace = null;
  let lastClickedLatLng = null;

  function initMap() {
    // Initialize map with a default view
    map = L.map('map');
    const defaultCenter = [20.0, 0.0];
    const defaultZoom = 2;
    map.setView(defaultCenter, defaultZoom);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // Restore previous view if available
    const savedView = localStorage.getItem('fh_map_view');
    if (savedView) {
      try {
        const saved = JSON.parse(savedView);
        if (typeof saved.lat === 'number' && typeof saved.lng === 'number' && typeof saved.zoom === 'number') {
          map.setView([saved.lat, saved.lng], saved.zoom);
        }
      } catch (e) { /* ignore parse errors */ }
    }

    // Persist view on move/zoom
    map.on('moveend', () => {
      const c = map.getCenter();
      const z = map.getZoom();
      localStorage.setItem('fh_map_view', JSON.stringify({ lat: c.lat, lng: c.lng, zoom: z }));
    });

    markersLayer = L.layerGroup().addTo(map);

    map.on('click', function (e) {
      lastClickedLatLng = e.latlng;
      const latInput = document.querySelector('#addPlaceModal input[name="latitude"]');
      const lngInput = document.querySelector('#addPlaceModal input[name="longitude"]');
      if (latInput && lngInput) {
        latInput.value = e.latlng.lat.toFixed(6);
        lngInput.value = e.latlng.lng.toFixed(6);
      }
    });

    loadPlaces();
  }

  async function loadPlaces(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`/api/places${query ? `?${query}` : ''}`);
    const places = await res.json();

    markersLayer.clearLayers();
    places.forEach(p => {
      const m = L.marker([p.latitude, p.longitude]).addTo(markersLayer);
      const content = `<div><strong>${p.name}</strong><br/><small>${p.cuisine_types || ''}</small><br/><button class="btn btn-sm btn-outline-primary mt-1" data-place-id="${p.id}" data-action="open">Details</button></div>`;
      m.bindPopup(content);
      m.on('popupopen', () => {
        setTimeout(() => {
          const btn = document.querySelector('button[data-place-id="' + p.id + '"][data-action="open"]');
          if (btn) btn.addEventListener('click', () => openPlaceModal(p.id));
        }, 0);
      });
    });
  }

  async function openPlaceModal(placeId) {
    const res = await fetch(`/api/places/${placeId}`);
    const p = await res.json();
    selectedPlace = p;

    document.getElementById('placeTitle').textContent = p.name;
    document.getElementById('placeDescription').textContent = p.description || '';
    document.getElementById('placeCuisines').textContent = p.cuisine_types || '';
    document.getElementById('placeDiet').textContent = p.diet_options || '';
    document.getElementById('placePrice').textContent = `${p.price_min ?? ''} - ${p.price_max ?? ''}`;
    document.getElementById('placeHours').textContent = p.hours || '';
    document.getElementById('placeContact').textContent = p.contact_info || '';
    const menuLink = document.getElementById('placeMenu');
    if (p.menu_url) { menuLink.href = p.menu_url; menuLink.classList.remove('d-none'); } else { menuLink.href = '#'; menuLink.classList.add('d-none'); }
    document.getElementById('likeCount').textContent = p.like_count || 0;
    document.getElementById('favoriteCount').textContent = p.favorite_count || 0;

    const imagesDiv = document.getElementById('placeImages');
    imagesDiv.innerHTML = '';
    (p.photo_urls || []).forEach(url => {
      const img = document.createElement('img');
      img.src = url;
      imagesDiv.appendChild(img);
    });

    const reviewsDiv = document.getElementById('reviewsList');
    reviewsDiv.innerHTML = '';
    (p.reviews || []).forEach(r => {
      const wrap = document.createElement('div');
      wrap.className = 'mb-2 p-2 border rounded';
      wrap.innerHTML = `<div><strong>${r.user_name || 'User'}</strong> <span class="text-warning">${'★'.repeat(r.rating)}${'☆'.repeat(5-r.rating)}</span> ${r.cost ? ` • $${r.cost}` : ''}</div>` +
                       `<div>${r.text || ''}</div>` +
                       `${r.image_url ? `<div class='mt-1'><img src='${r.image_url}' style='height:80px;border-radius:6px;object-fit:cover'/></div>` : ''}`;
      reviewsDiv.appendChild(wrap);
    });

    const modal = new bootstrap.Modal(document.getElementById('placeDetailModal'));
    modal.show();

    document.getElementById('btnLike').onclick = async () => {
      const res = await fetch(`/api/places/${p.id}/like`, { method: 'POST' });
      const body = await res.json();
      if (body.like_count !== undefined) document.getElementById('likeCount').textContent = body.like_count;
    };

    document.getElementById('btnFavorite').onclick = async () => {
      const res = await fetch(`/api/places/${p.id}/favorite`, { method: 'POST' });
      const body = await res.json();
      if (body.favorite_count !== undefined) document.getElementById('favoriteCount').textContent = body.favorite_count;
    };

    document.getElementById('btnDirections').onclick = async () => {
      if (!navigator.geolocation) return alert('Geolocation not supported');
      navigator.geolocation.getCurrentPosition((pos) => {
        const from = L.latLng(pos.coords.latitude, pos.coords.longitude);
        const to = L.latLng(p.latitude, p.longitude);
        if (routingControl) { map.removeControl(routingControl); routingControl = null; }
        routingControl = L.Routing.control({
          waypoints: [from, to],
          router: L.Routing.osrmv1({ serviceUrl: 'https://router.project-osrm.org/route/v1' }),
          show: false,
          addWaypoints: false,
          draggableWaypoints: false,
        }).addTo(map);
        map.fitBounds(L.latLngBounds([from, to]).pad(0.2));
      }, () => alert('Unable to get your location'));
    };

    const reviewForm = document.getElementById('reviewForm');
    if (reviewForm) {
      reviewForm.reset();
      reviewForm.querySelector('input[name="place_id"]').value = p.id;
      reviewForm.onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(reviewForm);
        const res = await fetch(`/api/places/${p.id}/review`, { method: 'POST', body: fd });
        if (res.ok) {
          await openPlaceModal(p.id);
        } else {
          alert('Failed to post review');
        }
      };
    }
  }

  function bindFilters() {
    const btn = document.getElementById('btnApplyFilters');
    btn.addEventListener('click', () => {
      const cuisine = document.getElementById('searchCuisine').value.trim();
      const priceMin = document.getElementById('priceMin').value;
      const priceMax = document.getElementById('priceMax').value;
      const diet = document.getElementById('dietOptions').value.trim();
      const params = {};
      if (cuisine) params.cuisine = cuisine;
      if (priceMin) params.price_min = priceMin;
      if (priceMax) params.price_max = priceMax;
      if (diet) params.diet = diet;
      loadPlaces(params);
    });
  }

  function bindAddPlaceForm() {
    const form = document.getElementById('addPlaceForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const res = await fetch('/api/places', { method: 'POST', body: fd });
      if (res.ok) {
        const modalEl = document.getElementById('addPlaceModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();
        form.reset();
        loadPlaces();
      } else {
        const body = await res.json().catch(() => ({}));
        alert(body.error || 'Failed to create place');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (document.getElementById('map')) {
      initMap();
    }
    bindFilters();
    bindAddPlaceForm();
  });
})();
