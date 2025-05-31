async function fetchTextFile(filename) {
  const res = await fetch(filename);
  if (!res.ok) throw new Error(`Failed to load ${filename}`);
  return res.text();
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

let users = [];
let categories = {};
let accessKey = '';
let binId = '';
let votes = {};

async function init() {
  try {
    setStatus('Loading configuration...');
    [users, categories, accessKey, binId] = await Promise.all([
      fetchTextFile('users.txt').then(txt => txt.trim().split('\n').filter(Boolean)),
      fetchTextFile('urls.txt').then(parseCategories),
      fetchTextFile('ACCESS_KEY.txt').then(txt => txt.trim()),
      fetchTextFile('BIN_ID.txt').then(txt => txt.trim())
    ]);
    populateUsers();
    await loadVotes();
    await renderListingsAndLoadAirbnbScript();
    setupCategoryScrollSpy();
  } catch (e) {
    setStatus('Error: ' + e.message);
  }
}

function parseCategories(txt) {
  const lines = txt.trim().split('\n');
  const cats = {};
  let currentCat = null;
  for (let line of lines) {
    line = line.trim();
    if (!line) continue;
    if (!line.startsWith('<')) {
      currentCat = line;
      cats[currentCat] = [];
    } else if (currentCat) {
      cats[currentCat].push(line);
    }
  }
  return cats;
}

function populateUsers() {
  const select = document.getElementById('userSelect');
  select.innerHTML = '';
  users.forEach(user => {
    const opt = document.createElement('option');
    opt.value = user;
    opt.textContent = user;
    select.appendChild(opt);
  });
}

async function loadVotes() {
  setStatus('Loading votes from jsonbin.io...');
  try {
    const res = await fetch(`https://api.jsonbin.io/v3/b/${binId}/latest`, {
      headers: { 'X-Master-Key': accessKey }
    });
    if (!res.ok) throw new Error('Failed to load votes');
    const data = await res.json();
    votes = data.record || {};
    setStatus('Votes loaded.');
  } catch (e) {
    votes = {};
    setStatus('Could not load votes. Starting fresh.');
  }
}

async function saveVotes() {
  setStatus('Saving votes to jsonbin.io...');
  try {
    const res = await fetch(`https://api.jsonbin.io/v3/b/${binId}`, {
      method: "PUT",
      headers: {
        'Content-Type': 'application/json',
        'X-Master-Key': accessKey
      },
      body: JSON.stringify(votes)
    });
    if (res.ok) {
      setStatus('Votes saved!');
    } else {
      setStatus('Failed to save votes.');
    }
  } catch (e) {
    setStatus('Failed to save votes: ' + e.message);
  }
}

// Extract the first href from the embed HTML (for the canonical link)
function extractFirstLink(embedHtml) {
  const match = embedHtml.match(/href="([^"]+)"/i);
  if (match) {
    // Decode HTML entities
    return match[1].replace(/&amp;/g, '&');
  }
  return null;
}

async function renderListingsAndLoadAirbnbScript() {
  renderListings();
  // Remove any previous Airbnb embed script
  const oldScript = document.getElementById('airbnb-embed-script');
  if (oldScript) oldScript.remove();

  // Dynamically load the Airbnb embed script
  const script = document.createElement('script');
  script.id = 'airbnb-embed-script';
  script.src = 'https://www.airbnb.com/embeddable/airbnb_jssdk';
  script.async = true;
  script.onload = () => {
    if (window.AirbnbEmbedFrame && typeof window.AirbnbEmbedFrame.init === 'function') {
      window.AirbnbEmbedFrame.init();
    }
  };
  document.body.appendChild(script);
  setupCategoryScrollSpy(); // re-setup after rerender
}

function renderListings() {
  const container = document.getElementById('listings');
  container.innerHTML = '';
  let globalIdx = 0;
  const catEntries = Object.entries(categories);
  catEntries.forEach(([cat, embeds], catIdx) => {
    // Category header (not sticky, but has a marker for scrollspy)
    const catHeader = document.createElement('h2');
    catHeader.className = 'category-header';
    catHeader.textContent = cat;
    catHeader.setAttribute('data-category', cat);
    container.appendChild(catHeader);

    embeds.forEach((embedDiv, embedIdx) => {
      const listingDiv = document.createElement('div');
      listingDiv.className = 'listing';
      listingDiv.innerHTML = `<div class="embed">${embedDiv}</div>`;

      // Extract and show the original link
      const fullLink = extractFirstLink(embedDiv);
      if (fullLink) {
        const linkDiv = document.createElement('div');
        linkDiv.className = 'direct-link';
        linkDiv.innerHTML = `<a href="${fullLink}" target="_blank">Direct link: ${fullLink}</a>`;
        listingDiv.appendChild(linkDiv);
      }

      // Voting controls
      const voteDiv = document.createElement('div');
      voteDiv.className = 'votes';
      voteDiv.innerHTML = renderVoteControls(cat, embedIdx, globalIdx);
      listingDiv.appendChild(voteDiv);
      container.appendChild(listingDiv);

      // Add event listeners for voting
      voteDiv.querySelectorAll('input[type=radio]').forEach(radio => {
        radio.addEventListener('change', () => handleVote(cat, embedIdx, globalIdx, radio.value));
      });
      globalIdx++;
    });

    // Add separator after each category except the last
    if (catIdx < catEntries.length -
