let currentSort = {
    column: 'price',
    order: 'asc'
};
let currentResults = [];  // Store results in memory
let filteredResults = []; // Store filtered results
let totalFoundAPI = 0;    // Store total found by API
let originalRawResults = []; // Store raw results before any TCO calculation for recalculation


function filterResults() {
    const filterText = document.getElementById('filterInput').value.toLowerCase();
    const negativeFilterText = document.getElementById('negativeFilterInput').value.toLowerCase();
    const hideNoCPUType = document.getElementById('hideNoCPUType').checked;
    const hideNoCPUModel = document.getElementById('hideNoCPUModel').checked;
    const hideNoRAM = document.getElementById('hideNoRAM').checked;
    const hideNoStorage = document.getElementById('hideNoStorage').checked;
    const hideNoPerformance = document.getElementById('hideNoPerformance').checked;
    const hideNoPerfPerDollar = document.getElementById('hideNoPerfPerDollar').checked;
    const hideNoFreeShipping = document.getElementById('hideNoFreeShipping').checked;
    const hideNoTCO = document.getElementById('hideNoTCO').checked;
    
    filteredResults = currentResults.filter(item => {
        const title = item.title ? item.title.toLowerCase() : '';
        const itemPrice = item.price !== null ? formatPrice(item.price).toLowerCase() : '';
        const itemPerformance = item.performance !== null ? String(item.performance) : '';
        const itemPerfPerDollar = item.performance_per_dollar !== null ? formatPerfPerDollar(item.performance_per_dollar).toLowerCase() : '';
        const itemTco = item.tco !== null ? formatPrice(item.tco).toLowerCase() : '';
        const cpuInfo = extractCPUInfo(item.cpu_model); // item.cpu_model is the original string like "i7-8700T"
        const cpuType = cpuInfo.type ? cpuInfo.type.toLowerCase() : '';
        const cpuModel = cpuInfo.model ? cpuInfo.model.toLowerCase() : '';
        const ram = item.ram ? item.ram.toLowerCase() : '';
        const storage = item.storage ? item.storage.toLowerCase() : '';

        // Check for negative filters first
        if (negativeFilterText) {
            const negativeSearchTerms = negativeFilterText.split(' ').filter(term => term.trim() !== '');
            if (negativeSearchTerms.some(term => 
                title.includes(term) || 
                (cpuType && cpuType.includes(term)) ||
                (cpuModel && cpuModel.includes(term)) ||
                (ram && ram.includes(term)) ||
                (storage && storage.includes(term))
            )) {
                return false; // Exclude if any negative term matches
            }
        }

        // Apply N/A filters
        if (hideNoCPUType && (!cpuInfo.type || cpuInfo.type === 'N/A')) return false;
        if (hideNoCPUModel && (!cpuInfo.model || cpuInfo.model === 'N/A')) return false;
        if (hideNoRAM && (!item.ram || item.ram === 'N/A' || item.ram.trim() === '')) return false;
        if (hideNoStorage && (!item.storage || item.storage === 'N/A' || item.storage.trim() === '')) return false;
        if (hideNoPerformance && (!item.performance || item.performance === 'N/A' || item.performance === 0)) return false;
        if (hideNoPerfPerDollar && (item.performance_per_dollar === null || item.performance_per_dollar === undefined)) return false;
        if (hideNoFreeShipping && !item.free_shipping) return false;
        if (hideNoTCO && (item.tco === null || item.tco === undefined)) return false;

        // Existing positive filter logic
        if (filterText) {
            const searchTerms = filterText.split(' ').filter(term => term.trim() !== '');
            const matchesAllTerms = searchTerms.every(term => 
                title.includes(term) || 
                itemPrice.includes(term) ||
                itemPerformance.includes(term) ||
                itemPerfPerDollar.includes(term) ||
                itemTco.includes(term) ||
                (cpuType && cpuType.includes(term)) ||
                (cpuModel && cpuModel.includes(term)) ||
                (ram && ram.includes(term)) ||
                (storage && storage.includes(term))
            );
            if (!matchesAllTerms) return false;
        }

        return true;
    });
    displayResults(filteredResults);
    updateSummary(); // Update count after filtering
}

function sortTable(column) {
    if (currentSort.column === column) {
        currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.order = 'asc';
    }
    updateSortIcons();
    // Sort and display current filteredResults
    sortResults(filteredResults); // Sorts filteredResults in place
    displayResults(filteredResults); // Display the newly sorted filteredResults
}

function displayResults(resultsToDisplay = filteredResults) { // Parameter renamed for clarity
    const resultsElement = document.getElementById('results');
    resultsElement.innerHTML = '';
    
    resultsToDisplay.forEach(listing => {
        const cpuInfo = extractCPUInfo(listing.cpu_model);
        const row = document.createElement('tr');
        row.setAttribute('data-item-id', listing.itemId);

        // Always default to AC adapter included to match our TCO calculation default
        const acAdapterIncluded = listing.manual_ac_adapter_included === undefined ? true : listing.manual_ac_adapter_included;

        let freeShipCellHTML = '';
        if (listing.free_shipping) {
            freeShipCellHTML = '✓';
        } else {
            if (listing.manual_shipping_override !== undefined && listing.manual_shipping_override !== null) {
                freeShipCellHTML = `<input type="number" class="shipping-override-inline" step="0.01" value="${listing.manual_shipping_override}" style="width: 60px;" onchange="handleItemTCOChange('${listing.itemId}')" onblur="handleItemTCOChange('${listing.itemId}')" placeholder="Cost">`;
            } else {
                freeShipCellHTML = `<span class="shipping-cost-placeholder" style="cursor:pointer; color:red; font-weight:bold;" onclick="showShippingInput(this, '${listing.itemId}')">✗</span>`;
            }
        }

        const renderCPUModel = (model) => {
            if (!model || model === 'N/A') return 'N/A';
            if (listing.title && 
                (listing.title.toLowerCase().includes('no cpu') || 
                 listing.title.toLowerCase().includes('without cpu'))) {
                return 'None';
            }
            return model;
        };
        
        const displayCpuModel = renderCPUModel(cpuInfo.model);

        // ------------ XSS mitigation ------------------
        const safeTitle = escapeHTML(listing.title);
        const safeUrl = sanitizeURL(listing.item_url);

        row.innerHTML = `
            <td><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeTitle}</a></td>
            <td>${formatPrice(listing.price)}</td>
            <td>${cpuInfo.type}</td>
            <td>${displayCpuModel}</td>
            <td>${listing.performance ? listing.performance.toLocaleString() : 'N/A'}</td>
            <td>${listing.ram || 'N/A'}</td>
            <td>${listing.storage || 'N/A'}</td>
            <td><input type="checkbox" class="ac-adapter-included" ${acAdapterIncluded ? 'checked' : ''} onchange="handleItemTCOChange('${listing.itemId}')"></td>
            <td class="free-ship-cell">${freeShipCellHTML}</td>
            <td class="tco-cell">${formatPrice(listing.tco)}</td>
            <td class="perf-per-dollar-cell">${formatPerfPerDollar(listing.performance_per_dollar)}</td>
        `;
        resultsElement.appendChild(row);
    });
}

function updateSummary() {
    const summaryElement = document.getElementById('results-summary');
    const shownCount = filteredResults.length; 
    if (shownCount > 0 || totalFoundAPI > 0) { 
         summaryElement.textContent = `Showing ${shownCount} of ${totalFoundAPI} total listings found by API.`;
    } else {
         summaryElement.textContent = ''; 
    }
}

function search() {
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');
    const filterInput = document.getElementById('filterInput');
    
    loading.style.display = 'block';
    loading.textContent = "Searching for deals...";
    results.innerHTML = '';
    filterInput.value = '';

    const checkboxes = document.querySelectorAll('.filter-row input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    
    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({}) 
    })
    .then(response => response.json())
    .then(data => {
        if (data.full_search_enabled) {
            loading.textContent = "Full search enabled. This may take a while...";
        } else {
            loading.textContent = "Searching for deals..."; 
        }
        
        if (data.status === 'success') {
            // console.log("Sample listing from backend with cpu_idle_power:", data.listings[0]?.cpu_idle_power);
            
            originalRawResults = data.listings.map(item => {
                const { tco, performance_per_dollar, ...rawItem } = { ...item };
                return rawItem;
            });
            
            populateTCOFields(data.tco_defaults);
            
            // Use TCO defaults from backend directly for the initial calculation round
            // This avoids any potential mismatch from reading DOM elements that might not be fully updated yet
            // or might have user-cached values if the page wasn't hard-refreshed.
            const initialTCOAssumptions = {
                kwh_cost: parseFloat(data.tco_defaults.kwh_cost),
                lifespan_years: parseInt(data.tco_defaults.lifespan_years, 10),
                shipping_cost_t_cpu: parseFloat(data.tco_defaults.shipping_cost_t_cpu),
                shipping_cost_non_t_cpu: parseFloat(data.tco_defaults.shipping_cost_non_t_cpu),
                required_ram_gb: parseInt(data.tco_defaults.required_ram_gb, 10),
                ram_upgrade_flat_cost: parseFloat(data.tco_defaults.ram_upgrade_flat_cost),
                required_storage_gb: parseInt(data.tco_defaults.required_storage_gb, 10),
                storage_upgrade_flat_cost: parseFloat(data.tco_defaults.storage_upgrade_flat_cost)
            };
            
            // console.log("Initial TCO assumptions for first calculation pass:", initialTCOAssumptions);
            
            currentResults = originalRawResults.map(item => {
                const newItem = { ...item }; 

                newItem.manual_ac_adapter_included = true;
                newItem.manual_shipping_override = undefined; 

                const initialOverrides = {
                    ac_adapter_included: newItem.manual_ac_adapter_included,
                    shipping: newItem.manual_shipping_override
                };
                
                // console.log(`Initial TCO for ${item.cpu_model || 'unknown'} (itemId: ${item.itemId}). Using newItem.manual_ac_adapter_included=${newItem.manual_ac_adapter_included}, newItem.manual_shipping_override=${newItem.manual_shipping_override}. Effective Overrides: ${JSON.stringify(initialOverrides)}`);
                const { tco, performance_per_dollar } = calculateTCOJS(item, initialTCOAssumptions, initialOverrides);
                
                newItem.tco = tco;
                newItem.performance_per_dollar = performance_per_dollar;
                
                return newItem;
            });
            
            totalFoundAPI = data.total_found || 0; 
            
            filteredResults = [...currentResults]; 
            
            sortResults(currentResults);
            displayResults(currentResults);
            updateSummary(); 
        } else {
            results.innerHTML = `<tr><td colspan="100%" style="text-align:center; color:red;">Error: ${data.message}</td></tr>`;
            currentResults = []; 
            filteredResults = [];
            originalRawResults = [];
            totalFoundAPI = 0;
            updateSummary(); 
        }
    })
    .catch(error => {
        console.error('Error during search:', error);
        results.innerHTML = `<tr><td colspan="100%" style="text-align:center; color:red;">An unexpected error occurred. Please check console.</td></tr>`;
        currentResults = []; 
        filteredResults = [];
        originalRawResults = [];
        totalFoundAPI = 0;
        updateSummary(); 
    })
    .finally(() => {
        loading.textContent = "Searching for deals...";
        loading.style.display = 'none';
    });
}

function handleItemTCOChange(itemId) {
    const itemIndex = originalRawResults.findIndex(item => item.itemId === itemId);
    if (itemIndex === -1) {
        console.error("Item not found in originalRawResults for ID:", itemId);
        return;
    }

    const assumptions = {
        kwh_cost: document.getElementById('kwh_cost').value,
        lifespan_years: document.getElementById('lifespan_years').value,
        shipping_cost_t_cpu: document.getElementById('shipping_cost_t_cpu').value,
        shipping_cost_non_t_cpu: document.getElementById('shipping_cost_non_t_cpu').value,
        required_ram_gb: document.getElementById('required_ram_gb').value,
        ram_upgrade_flat_cost: document.getElementById('ram_upgrade_flat_cost').value,
        required_storage_gb: document.getElementById('required_storage_gb').value,
        storage_upgrade_flat_cost: document.getElementById('storage_upgrade_flat_cost').value
    };

    const row = document.querySelector(`tr[data-item-id='${itemId}']`);
    if (!row) {
        console.error("Row not found for item ID:", itemId);
        return;
    }

    const currentItem = currentResults.find(item => item.itemId === itemId);
    if (!currentItem) {
        console.error("Item not found in currentResults for ID:", itemId);
        return;
    }

    const acAdapterCheckbox = row.querySelector('.ac-adapter-included');
    if (acAdapterCheckbox) { 
        currentItem.manual_ac_adapter_included = acAdapterCheckbox.checked;
        // console.log(`Item ${itemId} - Updated currentItem.manual_ac_adapter_included to: ${currentItem.manual_ac_adapter_included}`);
    }

    const freeShipCell = row.querySelector('.free-ship-cell');
    const inlineShippingInput = freeShipCell ? freeShipCell.querySelector('.shipping-override-inline') : null;
    if (inlineShippingInput) {
        currentItem.manual_shipping_override = inlineShippingInput.value === '' ? undefined : parseFloat(inlineShippingInput.value);
        // console.log(`Item ${itemId} - Updated currentItem.manual_shipping_override from input to: ${currentItem.manual_shipping_override}`);
    } else {
    }
    
    const itemSpecificOverrides = {
        ac_adapter_included: currentItem.manual_ac_adapter_included,
        shipping: currentItem.manual_shipping_override
    };

    const originalItem = { ...originalRawResults[itemIndex] }; 

    let tco, performance_per_dollar;
    if (originalItem.cpu_idle_power === null || originalItem.cpu_idle_power === undefined) {
        // console.log(`TCO for ${originalItem.cpu_model || "unknown"} (${itemId}): N/A (missing power data) - checkbox has no effect`);
        tco = null;
        performance_per_dollar = null;
    } else {
        ({ tco, performance_per_dollar } = calculateTCOJS(originalItem, assumptions, itemSpecificOverrides)); 
    }

    currentItem.tco = tco;
    currentItem.performance_per_dollar = performance_per_dollar;

    const tcoCell = row.querySelector('.tco-cell');
    const perfPerDollarCell = row.querySelector('.perf-per-dollar-cell');
    if (tcoCell) tcoCell.textContent = formatPrice(tco);
    if (perfPerDollarCell) perfPerDollarCell.textContent = formatPerfPerDollar(performance_per_dollar);
    
}

function showShippingInput(placeholderElement, itemId) {
    const cell = placeholderElement.parentElement;
    if (!cell || cell.classList.contains('free-ship-cell') === false) {
        console.error("Parent cell for shipping input not found or incorrect.");
        return;
    }
    const existingInput = cell.querySelector('.shipping-override-inline');
    if (existingInput) return; 

    const input = document.createElement('input');
    input.type = 'number';
    input.className = 'shipping-override-inline';
    input.step = '0.01';
    input.style.width = '60px'; 
    input.placeholder = 'Cost';
    
    input.onchange = () => handleItemTCOChange(itemId);
    input.onblur = () => {
        handleItemTCOChange(itemId);
    };
    
    const currentItem = currentResults.find(item => item.itemId === itemId);
    if (currentItem && currentItem.manual_shipping_override !== undefined && currentItem.manual_shipping_override !== null) {
        input.value = currentItem.manual_shipping_override;
    }

    placeholderElement.style.display = 'none'; 
    cell.appendChild(input);
    input.focus();
}

function recalculateAndDisplay() {
    // console.log("recalculateAndDisplay called. Current lifespan_years input value:", document.getElementById('lifespan_years').value);
    
    const assumptions = {
        kwh_cost: parseFloat(document.getElementById('kwh_cost').value),
        lifespan_years: parseInt(document.getElementById('lifespan_years').value, 10),
        shipping_cost_t_cpu: parseFloat(document.getElementById('shipping_cost_t_cpu').value),
        shipping_cost_non_t_cpu: parseFloat(document.getElementById('shipping_cost_non_t_cpu').value),
        required_ram_gb: parseInt(document.getElementById('required_ram_gb').value, 10),
        ram_upgrade_flat_cost: parseFloat(document.getElementById('ram_upgrade_flat_cost').value),
        required_storage_gb: parseInt(document.getElementById('required_storage_gb').value, 10),
        storage_upgrade_flat_cost: parseFloat(document.getElementById('storage_upgrade_flat_cost').value)
    };
    
    // console.log("Recalculating with assumptions:", assumptions);

    if (assumptions.lifespan_years <= 0) {
        // console.log("Lifespan was <=0, adjusting to 1.");
        assumptions.lifespan_years = 1;
    }

    currentResults = originalRawResults.map(item => {
        const newItem = { ...item }; 
        
        const prevItemState = currentResults.find(cr => cr.itemId === item.itemId);

        if (prevItemState) {
            newItem.manual_ac_adapter_included = prevItemState.manual_ac_adapter_included;
            newItem.manual_shipping_override = prevItemState.manual_shipping_override;
            // console.log(`Global Recalc for ${item.cpu_model || 'unknown'} (${item.itemId}): Found prev state. manual_ac_adapter_included=${newItem.manual_ac_adapter_included}, manual_shipping_override=${newItem.manual_shipping_override}`);
        } else {
            newItem.manual_ac_adapter_included = true;
            newItem.manual_shipping_override = undefined;
            // console.log(`Global Recalc for ${item.cpu_model || 'unknown'} (${item.itemId}): No prev state found. Initializing manual_ac_adapter_included=true, manual_shipping_override=undefined`);
        }
        
        const itemSpecificOverrides = {
            ac_adapter_included: newItem.manual_ac_adapter_included,
            shipping: newItem.manual_shipping_override
        };
        
        const { tco, performance_per_dollar } = calculateTCOJS(item, assumptions, itemSpecificOverrides);
        
        newItem.tco = tco;
        newItem.performance_per_dollar = performance_per_dollar;
        
        return newItem;
    });
    
    sortResults(currentResults);
    
    filterResults();
}


document.addEventListener('DOMContentLoaded', () => {
    updateSortIcons(); 

    const tcoInputIds = [
        'kwh_cost', 'lifespan_years', 'shipping_cost_t_cpu', 'shipping_cost_non_t_cpu',
        'required_ram_gb', 'ram_upgrade_flat_cost', 'required_storage_gb', 'storage_upgrade_flat_cost'
    ];
    tcoInputIds.forEach(id => {
        const inputElement = document.getElementById(id);
        if (inputElement) {
            inputElement.addEventListener('change', function() { 
                // console.log(`TCO assumption input '${this.id}' changed. New value: ${this.value}. Attempting to call recalculateAndDisplay.`); 
                try {
                    recalculateAndDisplay();
                    // console.log("recalculateAndDisplay was called successfully after change in", this.id);
                } catch (e) {
                    console.error("Error calling recalculateAndDisplay from TCO input change:", e);
                }
            });
        }
    });
});

function sortResults(resultsArray) {
    resultsArray.sort((a, b) => { 
        let aVal = a[currentSort.column];
        let bVal = b[currentSort.column];

        if (currentSort.column === 'cpu_type') {
            aVal = extractCPUInfo(a.cpu_model).type;
            bVal = extractCPUInfo(b.cpu_model).type;
        } else if (currentSort.column === 'cpu_model') {
            aVal = extractCPUInfo(a.cpu_model).model;
            bVal = extractCPUInfo(b.cpu_model).model;
        }

        if (currentSort.column === 'tco' || currentSort.column === 'performance_per_dollar') {
            const isANull = aVal === null || aVal === undefined || aVal === 'N/A';
            const isBNull = bVal === null || bVal === undefined || bVal === 'N/A';
            
            if (isANull && !isBNull) return 1; 
            if (!isANull && isBNull) return -1; 
            if (isANull && isBNull) return 0; 
            
            const numA = parseFloat(aVal);
            const numB = parseFloat(bVal);
            
            return (currentSort.order === 'asc' ? 1 : -1) * (numA - numB);
        }

        const isANull = aVal === null || aVal === undefined || aVal === 'N/A' || String(aVal).trim() === '';
        const isBNull = bVal === null || bVal === undefined || bVal === 'N/A' || String(bVal).trim() === '';

        if (isANull && isBNull) return 0;
        if (isANull) return currentSort.order === 'asc' ? 1 : -1;
        if (isBNull) return currentSort.order === 'asc' ? -1 : 1;
        
        if (['price', 'performance'].includes(currentSort.column)) {
            const numA = parseFloat(aVal);
            const numB = parseFloat(bVal);
            if (isNaN(numA) && isNaN(numB)) return 0;
            if (isNaN(numA)) return currentSort.order === 'asc' ? 1 : -1;
            if (isNaN(numB)) return currentSort.order === 'asc' ? -1 : 1;
            return (currentSort.order === 'asc' ? 1 : -1) * (numA - numB);
        }
        
        if (currentSort.column === 'ram' || currentSort.column === 'storage') {
            const aNum = parseInt(aVal) || 0;
            const bNum = parseInt(bVal) || 0;
            const aGB = String(aVal).toLowerCase().includes('tb') ? aNum * 1024 : aNum;
            const bGB = String(bVal).toLowerCase().includes('tb') ? bNum * 1024 : bNum;
            return (currentSort.order === 'asc' ? 1 : -1) * (aGB - bGB);
        }

        if (currentSort.column === 'free_shipping') {
            const aBool = Boolean(aVal);
            const bBool = Boolean(bVal);
            if (aBool === bBool) return 0;
            return (currentSort.order === 'asc' ? 1 : -1) * (aBool ? -1 : 1);
        }

        if (currentSort.column === 'cpu_model') {
            const aNum = parseInt(String(aVal).replace(/[^\d]/g, '')) || 0;
            const bNum = parseInt(String(bVal).replace(/[^\d]/g, '')) || 0;
            if (aNum === 0 && bNum === 0) { 
                 return (currentSort.order === 'asc' ? 1 : -1) * String(aVal).localeCompare(String(bVal));
            }
            if (aNum === 0) return currentSort.order === 'asc' ? 1 : -1;
            if (bNum === 0) return currentSort.order === 'asc' ? -1 : 1;
            return (currentSort.order === 'asc' ? 1 : -1) * (aNum - bNum);
        }
        
        if (currentSort.column === 'title' || currentSort.column === 'cpu_type') {
             return (currentSort.order === 'asc' ? 1 : -1) * 
                String(aVal).localeCompare(String(bVal));
        }
        return 0;
    });
}

function updateSortIcons() {
    document.querySelectorAll('th .sort-icon').forEach(icon => {
        icon.className = 'sort-icon'; 
    });
    const currentHeader = document.querySelector(`th[onclick*="sortTable('${currentSort.column}')"]`);
    if (currentHeader) {
        const icon = currentHeader.querySelector('.sort-icon');
        if (icon) {
            icon.className = `sort-icon sort-${currentSort.order}`;
        }
    }
} 