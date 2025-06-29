// TCO related functions will be moved here

function calculateTCOJS(item, assumptions, overrides = {}) {
    const itemCPU = item.cpu_model || "unknown";
    const itemId = item.itemId;

    console.log(`[TCO_CALC_START] Item: ${itemCPU} (${itemId}) | Price: ${item.price} | Idle Power: ${item.cpu_idle_power} | Overrides: ${JSON.stringify(overrides)} | Assumptions: ${JSON.stringify(assumptions)}`);

    if (item.cpu_idle_power === null || item.cpu_idle_power === undefined) {
        console.log(`[TCO_CALC_END] Item: ${itemCPU} (${itemId}) - Result: N/A (No idle power data)`);
        return { tco: null, performance_per_dollar: null };
    }

    if (item.price === null || item.price === undefined) {
        console.log(`[TCO_CALC_END] Item: ${itemCPU} (${itemId}) - Result: N/A (No price data)`);
        return { tco: null, performance_per_dollar: null };
    }

    const numericPrice = parseFloat(item.price);
    const idleWatts = parseFloat(item.cpu_idle_power);
    
    const kwhCost = parseFloat(assumptions.kwh_cost);
    const lifespanYears = parseInt(assumptions.lifespan_years, 10);
    // Ensure lifespanYears is at least 1 for calculation, but log the original if it was <= 0
    let safeLifespanYears = lifespanYears;
    if (lifespanYears <= 0) {
        console.log(`[TCO_INFO] Item: ${itemCPU} (${itemId}) - Lifespan years was ${lifespanYears}, using 1 for energy calculation.`);
        safeLifespanYears = 1;
    }

    const energyCostCalc = (idleWatts / 1000) * (24 * 365 * safeLifespanYears) * kwhCost;
    
    let shippingCostToAdd = 0;
    const defaultShippingT = parseFloat(assumptions.shipping_cost_t_cpu);
    const defaultShippingNonT = parseFloat(assumptions.shipping_cost_non_t_cpu);

    if (overrides.shipping !== undefined && overrides.shipping !== null && overrides.shipping !== '') {
        shippingCostToAdd = parseFloat(overrides.shipping);
    } else if (!item.free_shipping) {
        if (item.cpu_model && typeof item.cpu_model === 'string' && item.cpu_model.toUpperCase().endsWith('T')) {
            shippingCostToAdd = defaultShippingT;
        } else {
            shippingCostToAdd = defaultShippingNonT;
        }
    }
    
    let ramShortfallCost = 0;
    const itemRamGb = parseCapacityToGBJS(item.ram);
    const requiredRamGb = parseFloat(assumptions.required_ram_gb);
    const ramUpgradeCost = parseFloat(assumptions.ram_upgrade_flat_cost);
    if (itemRamGb < requiredRamGb) {
        ramShortfallCost = ramUpgradeCost;
    }
    
    let storageShortfallCost = 0;
    const itemStorageGb = parseCapacityToGBJS(item.storage);
    const requiredStorageGb = parseFloat(assumptions.required_storage_gb);
    const storageUpgradeCost = parseFloat(assumptions.storage_upgrade_flat_cost);
    if (itemStorageGb < requiredStorageGb) {
        storageShortfallCost = storageUpgradeCost;
    }

    let acAdapterCost = 0;
    const acAdapterActuallyIncluded = overrides.ac_adapter_included === undefined ? true : overrides.ac_adapter_included;
    if (!acAdapterActuallyIncluded) {
        acAdapterCost = 10; // Hardcoded $10 for AC adapter
    }
    
    const tco = numericPrice + energyCostCalc + shippingCostToAdd + ramShortfallCost + storageShortfallCost + acAdapterCost;
    
    let performancePerDollar = null;
    if (item.performance && tco && tco > 0) {
        performancePerDollar = parseFloat(item.performance) / tco;
    }

    console.log(`[TCO_BREAKDOWN] Item: ${itemCPU} (${itemId})`);
    console.log(`  Price: ${numericPrice.toFixed(2)}`);
    console.log(`  Energy Cost: ${energyCostCalc.toFixed(2)} (Idle: ${idleWatts}W, Lifespan: ${safeLifespanYears}yrs, kWh Cost: ${kwhCost})`);
    console.log(`  Shipping Cost: ${shippingCostToAdd.toFixed(2)} (Free: ${item.free_shipping}, Override: ${overrides.shipping}, Default T: ${defaultShippingT}, Default Non-T: ${defaultShippingNonT})`);
    console.log(`  RAM Shortfall: ${ramShortfallCost.toFixed(2)} (Item RAM: ${itemRamGb}GB, Required: ${requiredRamGb}GB, Upgrade Cost: ${ramUpgradeCost})`);
    console.log(`  Storage Shortfall: ${storageShortfallCost.toFixed(2)} (Item Storage: ${itemStorageGb}GB, Required: ${requiredStorageGb}GB, Upgrade Cost: ${storageUpgradeCost})`);
    console.log(`  AC Adapter Cost: ${acAdapterCost.toFixed(2)} (Included by override/default: ${acAdapterActuallyIncluded})`);
    console.log(`  --------------------`);
    console.log(`  Calculated TCO: ${isNaN(tco) ? 'N/A' : tco.toFixed(2)}`);
    console.log(`  Performance Score: ${item.performance || 'N/A'}`);
    console.log(`  Calculated Perf/$: ${performancePerDollar ? (isNaN(performancePerDollar) ? 'N/A' : performancePerDollar.toFixed(1)) : 'N/A'}`);
    console.log(`[TCO_CALC_END] Item: ${itemCPU} (${itemId}) - Assumptions Used: ${JSON.stringify(assumptions)}, Overrides Used: ${JSON.stringify(overrides)}`);
    
    return { tco: isNaN(tco) ? null : tco, performance_per_dollar: (performancePerDollar && !isNaN(performancePerDollar)) ? performancePerDollar : null };
}

function populateTCOFields(tcoDefaults) {
    if (!tcoDefaults) return;
    document.getElementById('kwh_cost').value = tcoDefaults.kwh_cost;
    document.getElementById('lifespan_years').value = tcoDefaults.lifespan_years;
    document.getElementById('shipping_cost_t_cpu').value = tcoDefaults.shipping_cost_t_cpu;
    document.getElementById('shipping_cost_non_t_cpu').value = tcoDefaults.shipping_cost_non_t_cpu;
    document.getElementById('required_ram_gb').value = tcoDefaults.required_ram_gb;
    document.getElementById('ram_upgrade_flat_cost').value = tcoDefaults.ram_upgrade_flat_cost;
    document.getElementById('required_storage_gb').value = tcoDefaults.required_storage_gb;
    document.getElementById('storage_upgrade_flat_cost').value = tcoDefaults.storage_upgrade_flat_cost;
}

function toggleTCOAssumptions() {
    const form = document.getElementById('tcoAssumptionsForm');
    const button = document.getElementById('tcoToggleButton');
    if (form.style.display === 'none') {
        form.style.display = 'grid'; 
        button.textContent = 'Adjust TCO Assumptions ▲';
    } else {
        form.style.display = 'none';
        button.textContent = 'Adjust TCO Assumptions ▼';
    }
} 