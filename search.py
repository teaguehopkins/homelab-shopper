from rich.table import Table

# Create the table
table = Table(show_header=True, header_style="bold magenta")
table.add_column("Price", justify="right")
table.add_column("CPU Type", justify="left")
table.add_column("CPU Model", justify="left")
table.add_column("Performance", justify="right")
table.add_column("Perf/$", justify="right")
table.add_column("Free Shipping", justify="center")
table.add_column("Link", justify="left", no_wrap=True)

# Add rows to the table
for item in sorted_items:
    # Get CPU details
    cpu_type = item.get('cpu_type', 'N/A')
    cpu_model = item.get('cpu_model', 'N/A')
    
    # Get performance score
    performance = item.get('performance', 'N/A')
    if performance != 'N/A':
        performance = f"{performance:,}"
        
    # Get performance per dollar
    perf_per_dollar = item.get('perf_per_dollar', 'N/A')
    if perf_per_dollar != 'N/A':
        perf_per_dollar = f"${perf_per_dollar:,.2f}"
        
    # Check for free shipping
    free_shipping = "✓" if item.get('free_shipping', False) else "✗"
    
    table.add_row(
        f"${item['price']:,.2f}",
        cpu_type,
        cpu_model,
        performance,
        perf_per_dollar,
        free_shipping,
        item['link']
    )

def process_search_results(results):
    """Process search results and extract relevant information."""
    processed_items = []
    
    for item in results:
        # Extract price
        price_text = item.get('price', 'N/A')
        if price_text != 'N/A':
            try:
                # Remove currency symbol and commas, then convert to float
                price = float(price_text.replace('$', '').replace(',', ''))
            except ValueError:
                price = float('inf')  # Set to infinity if price can't be parsed
        else:
            price = float('inf')
            
        # Extract CPU information
        title = item.get('title', '').lower()
        cpu_type = 'N/A'
        cpu_model = 'N/A'
        
        # Check for free shipping
        free_shipping = False
        shipping_info = item.get('shipping', '').lower()
        if 'free shipping' in shipping_info or 'free delivery' in shipping_info:
            free_shipping = True
            
        # Look for CPU type and model in title
        for cpu in CPU_MODELS:
            if cpu['name'].lower() in title:
                cpu_type = cpu['name']
                # Try to extract the model number
                model_match = re.search(r'\b\d{4}[a-z]?\b', title)
                if model_match:
                    cpu_model = model_match.group(0)
                break
                
        # Get performance score if available
        performance = 'N/A'
        perf_per_dollar = 'N/A'
        if cpu_type != 'N/A':
            for cpu in CPU_MODELS:
                if cpu['name'] == cpu_type:
                    performance = cpu['score']
                    if price != float('inf'):
                        perf_per_dollar = performance / price
                    break
        
        processed_items.append({
            'title': item.get('title', 'N/A'),
            'price': price,
            'cpu_type': cpu_type,
            'cpu_model': cpu_model,
            'performance': performance,
            'perf_per_dollar': perf_per_dollar,
            'free_shipping': free_shipping,
            'link': item.get('link', 'N/A')
        })
    
    return processed_items 