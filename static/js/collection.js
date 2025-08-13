// collection.js

document.addEventListener('DOMContentLoaded', function() {
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

    sortPriceSgdHeader.style.cursor = 'pointer';
    sortIcon.innerHTML = '&#9650;';

    sortPriceSgdHeader.addEventListener('click', () => {
        const rows = Array.from(tableBody.querySelectorAll('tr'));
        rows.sort((a, b) => {
            const priceA = parseFloat(a.cells[8].dataset.sortValue);
            const priceB = parseFloat(b.cells[8].dataset.sortValue);

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

    // Price per Unit (Yen) Calculation Logic
    const divisorInputs = document.querySelectorAll('.divisor-input-yen');

    divisorInputs.forEach(input => {
        input.addEventListener('input', function() {
            const priceCell = this.closest('td');
            const row = this.closest('tr');
            const originalPrice = parseFloat(priceCell.dataset.originalPrice);
            const originalCurrency = priceCell.dataset.originalCurrency;
            const sgdPrice = parseFloat(priceCell.dataset.sgdPrice);
            const divisor = parseFloat(this.value);

            const resultSpan = priceCell.querySelector('.result-span-yen');
            const totalSgdCell = row.querySelector('.total-price-sgd-cell');
            
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
});