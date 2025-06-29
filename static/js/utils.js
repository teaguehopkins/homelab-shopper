function formatPrice(price) {
    if (price === null || price === undefined) return 'N/A';
    if (isNaN(price)) return 'Invalid'; // Handle NaN
    return '$' + parseFloat(price).toFixed(2);
}

function extractCPUInfo(cpuString) {
    if (!cpuString || cpuString === 'N/A') return { type: 'N/A', model: 'N/A' };
    
    // Try to match Intel Core iX series (e.g., i7-8700T)
    const iXMatch = cpuString.match(/^(i[3579])(?:[\s-]?(\d{4,5}[a-z\d]*))?$/i);
    if (iXMatch) {
        return {
            type: iXMatch[1].toUpperCase(), // i3, i5, i7, i9
            model: iXMatch[2] ? iXMatch[2].toUpperCase() : 'N/A' // Model number like 8700T or N/A if just i7
        };
    }

    // Try to match Intel N-series (e.g., N100, N305)
    const nSeriesMatch = cpuString.match(/^(N\d{3,4})$/i);
    if (nSeriesMatch) {
        return {
            type: 'N-SERIES', 
            model: nSeriesMatch[1].toUpperCase()
        };
    }
    
    return { type: 'N/A', model: 'N/A' };
}

function formatPerfPerDollar(value) {
    if (value === null || value === undefined) return 'N/A';
    if (isNaN(value)) return 'Invalid'; // Handle NaN
    return parseFloat(value).toFixed(1); // Format to 1 decimal place
}

function parseCapacityToGBJS(capacityStr) {
    if (!capacityStr || capacityStr.toUpperCase() === 'N/A') {
        return 0;
    }
    capacityStr = capacityStr.toUpperCase();
    const numPartMatch = capacityStr.match(/(\d+\.\d+|\d+)/); 

    if (!numPartMatch) {
        return 0;
    }

    try {
        const val = parseFloat(numPartMatch[0]);
        if (capacityStr.includes('TB')) {
            return parseInt(val * 1024);
        }
        if (capacityStr.includes('GB')) {
            return parseInt(val);
        }
        return parseInt(val); 
    } catch (e) {
        return 0;
    }
}

// -------------------------------------------------------------------
// Security helpers: mitigate XSS from untrusted API data
// -------------------------------------------------------------------

/**
 * Return a version of `str` with HTML special characters escaped so it can
 * be safely inserted into innerHTML.
 */
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"'`]/g, function (c) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '`': '&#96;'
        }[c];
    });
}

/**
 * Validate that a URL has http/https scheme and return it; otherwise return '#'.
 */
function sanitizeURL(url) {
    try {
        const u = new URL(url);
        if (u.protocol === 'http:' || u.protocol === 'https:') {
            return u.href;
        }
    } catch (e) {
        // fallthrough
    }
    return '#';
} 