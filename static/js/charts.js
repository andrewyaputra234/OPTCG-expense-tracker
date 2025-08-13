// static/js/charts.js
document.addEventListener('DOMContentLoaded', function() {

    // =========================================================
    // Chart.js Logic (for the Collection Value Chart)
    // =========================================================
    const collectionValueCtx = document.getElementById('collectionValueChart');
    if (collectionValueCtx) {
        new Chart(collectionValueCtx, {
            type: 'bar',
            data: {
                labels: typeof cardNames !== 'undefined' ? cardNames : [],
                datasets: [{
                    label: 'Current Card Value (SGD)',
                    data: typeof cardValues !== 'undefined' ? cardValues : [],
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

    // =========================================================
    // Rotating GIF Card Logic
    // =========================================================
    const images = document.querySelectorAll('.rotating-card-image');
    let currentIndex = 0;

    if (images.length > 0) {
        // Ensure the first image is active on load
        images[currentIndex].classList.add('active');

        function rotateImages() {
            images[currentIndex].classList.remove('active');
            currentIndex = (currentIndex + 1) % images.length;
            images[currentIndex].classList.add('active');
        }

        setInterval(rotateImages, 5000);
    }
});