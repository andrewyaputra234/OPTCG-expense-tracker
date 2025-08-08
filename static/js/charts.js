// static/js/charts.js
document.addEventListener('DOMContentLoaded', function() {
    // This is where your Chart.js code will go.
    // For example, to draw the collection value chart:
    const collectionValueCtx = document.getElementById('collectionValueChart');
    if (collectionValueCtx) {
        // These variables (cardNames, cardValues) will be passed from Jinja2 in collection.html
        new Chart(collectionValueCtx, {
            type: 'bar', // Can be 'pie', 'line', etc.
            data: {
                labels: typeof cardNames !== 'undefined' ? cardNames : [], // Check if defined
                datasets: [{
                    label: 'Current Card Value (SGD)',
                    data: typeof cardValues !== 'undefined' ? cardValues : [], // Check if defined
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Card Values in Your Collection'
                    }
                }
            }
        });
    }

    // Add more chart logic here for expenses, etc. as you develop
    const expenseChartCtx = document.getElementById('expenseCategoryChart');
    if (expenseChartCtx) {
         // expense_labels and expense_data will come from Flask via Jinja2
         new Chart(expenseChartCtx, {
            type: 'pie',
            data: {
                labels: typeof expenseLabels !== 'undefined' ? expenseLabels : [],
                datasets: [{
                    data: typeof expenseData !== 'undefined' ? expenseData : [],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(153, 102, 255, 0.6)',
                        'rgba(255, 159, 64, 0.6)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    borderWidth: 1
                ]
            }
        });
    }

});