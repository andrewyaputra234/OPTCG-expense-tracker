// collection.js

document.addEventListener('DOMContentLoaded', function() {
    // ---- EXISTING FUNCTIONS (KEPT AS-IS) ----

    // Function to recalculate and update the subtotal
    function updateSubtotal() {
        let total = 0;
        document.querySelectorAll('.total-price-sgd-cell').forEach(cell => {
            const value = parseFloat(cell.dataset.sortValue);
            if (!isNaN(value)) {
                total += value;
            }
        });
        const subtotalElement = document.getElementById('subtotalPriceSgd');
        subtotalElement.textContent = '$' + total.toFixed(2) + ' SGD';
        subtotalElement.dataset.basePrice = total.toFixed(2);

        // Also update mailing fee if checked
        const checkbox = document.getElementById('mailingFeeCheckbox');
        if (checkbox.checked) {
            const totalWithMailing = total + 3.50;
            document.getElementById('totalPriceWithMailingSgd').textContent = '$' + totalWithMailing.toFixed(2) + ' SGD';
        }
    }

    // Mailing Fee Logic
    const checkbox = document.getElementById('mailingFeeCheckbox');
    const subtotalElement = document.getElementById('subtotalPriceSgd');
    const totalWithMailingContainer = document.getElementById('totalWithMailingFeeContainer');
    const totalWithMailingElement = document.getElementById('totalPriceWithMailingSgd');
    const mailingFee = 3.50;
    
    checkbox.addEventListener('change', function() {
        const currentSubtotal = parseFloat(subtotalElement.dataset.basePrice);
        if (this.checked) {
            const totalWithMailing = currentSubtotal + mailingFee;
            totalWithMailingElement.textContent = '$' + totalWithMailing.toFixed(2) + ' SGD';
            totalWithMailingContainer.style.display = 'block';
        } else {
            totalWithMailingContainer.style.display = 'none';
        }
    });

    // Table Sorting Logic
    const sortPriceSgdHeader = document.getElementById('sortPriceSgd');
    const sortIcon = document.getElementById('sortIcon');
    const tableBody = document.querySelector('#cardTable tbody');
    let isAscending = true;

    if (sortPriceSgdHeader) { // Check if the header exists before adding event listener
        sortPriceSgdHeader.style.cursor = 'pointer';
        sortIcon.innerHTML = '&#9650;';

        sortPriceSgdHeader.addEventListener('click', () => {
            const rows = Array.from(tableBody.querySelectorAll('tr'));
            rows.sort((a, b) => {
                // Adjust index to 9 to account for the new "Live Price" column
                const priceA = parseFloat(a.cells[9].dataset.sortValue);
                const priceB = parseFloat(b.cells[9].dataset.sortValue);

                if (isAscending) {
                    return priceA - priceB;
                } else {
                    return priceB - priceA;
                }
            });

            rows.forEach(row => tableBody.appendChild(row));
            isAscending = !isAscending;
            sortIcon.innerHTML = isAscending ? '&#9650;' : '&#9660;';
        });
    }

    // Price per Unit (Yen) Calculation Logic - FIXED
    const divisorInputs = document.querySelectorAll('.divisor-input-yen');

    divisorInputs.forEach(input => {
        input.addEventListener('input', function() {
            const priceCell = this.closest('td');
            const row = this.closest('tr');
            const originalPrice = parseFloat(priceCell.dataset.originalPrice);
            const originalCurrency = priceCell.dataset.originalCurrency;
            
            // CORRECT: Get the original SGD price from the data attribute on the total price cell
            const totalSgdCell = row.querySelector('.total-price-sgd-cell');
            const sgdPrice = parseFloat(totalSgdCell.dataset.sortValue);

            const divisor = parseFloat(this.value);
            const resultSpan = priceCell.querySelector('.result-span-yen');
            
            if (originalCurrency === 'JPY') {
                if (isNaN(divisor) || divisor === 0) {
                    resultSpan.textContent = '0.00';
                    totalSgdCell.textContent = '$' + sgdPrice.toFixed(2);
                    totalSgdCell.dataset.sortValue = sgdPrice;
                } else {
                    const newTotalSgd = originalPrice / divisor;
                    resultSpan.textContent = newTotalSgd.toFixed(2);
                    totalSgdCell.textContent = '$' + newTotalSgd.toFixed(2);
                    totalSgdCell.dataset.sortValue = newTotalSgd;
                }
                updateSubtotal();
            } 
        });
    });

    const generateBtn = document.getElementById('generateMessageBtn');
    const mailingFeeCheckbox = document.getElementById('mailingFeeCheckbox');
    
    // **IMPORTANT: Replace with your actual phone number and name**
    const phoneNumber = '91275288';
    const name = 'Andrew';

    if (generateBtn) {
        generateBtn.addEventListener('click', function() {
            let subtotalPrice = parseFloat(subtotalElement.getAttribute('data-base-price'));
            let mailingText = '';
            
            if (mailingFeeCheckbox.checked) {
                subtotalPrice += 3.50;
                mailingText = '(inclusive of mailing)';
            }

            const message = `Hello, thanks for the support of my sales. If the above info in the picture is correct, please xfer $${subtotalPrice.toFixed(2)}${mailingText} to ${phoneNumber}(${name}) and provide me a screenshot + your mailing details.`;
            
            navigator.clipboard.writeText(message).then(() => {
                alert('Sale message copied to clipboard!');
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                alert('Failed to copy the message. Please copy it manually:\n\n' + message);
            });
        });
    }

    // ---- NEW LIVE PRICING FUNCTIONALITY ----
    const livePriceButtons = document.querySelectorAll('.live-price-btn');

    livePriceButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const card_number = button.dataset.cardNumber;
            const livePriceContainer = button.parentElement.querySelector('.live-prices-container');

            // Show a loading state
            button.innerText = 'Fetching...';
            button.disabled = true;

            try {
                const response = await fetch(`/get_live_price/${card_number}`);
                const data = await response.json();

                if (response.ok && data.prices) {
                    // Create a list to hold the prices
                    const priceList = document.createElement('ul');
                    priceList.classList.add('list-unstyled', 'mb-0');

                    data.prices.forEach(priceItem => {
                        const listItem = document.createElement('li');
                        // Use a line break for each price item to display them clearly
                        listItem.innerHTML = `${priceItem.rarity}: **¥${priceItem.price_yen}**`;
                        priceList.appendChild(listItem);
                    });

                    // Clear the button and append the new list of prices
                    button.style.display = 'none'; // Hide the button
                    livePriceContainer.appendChild(priceList);

                } else {
                    livePriceContainer.innerText = 'No live price found.';
                    livePriceContainer.classList.add('text-danger');
                    button.style.display = 'none';
                }
            } catch (error) {
                console.error('Error fetching live price:', error);
                livePriceContainer.innerText = 'Error fetching price.';
                livePriceContainer.classList.add('text-danger');
                button.style.display = 'none';
            }
        });
    });
});