// nav_script.js

const hamburgerMenu = document.querySelector("#hamburger-menu");
const overlay = document.querySelector("#overlay");
const navItems = document.querySelectorAll("nav ul li");

// Control Navigation Animation
function navAnimation(val1, val2) {
    navItems.forEach((nav, i) => {
        nav.classList.replace(`slide-${val1}-${i + 1}`, `slide-${val2}-${i + 1}`);
    });
}

function toggleNav() {
    // Toggle: Hamburger Open/Close
    hamburgerMenu.classList.toggle("active");

    // Toggle: Menu Active
    overlay.classList.toggle("overlay-active");

    if (overlay.classList.contains("overlay-active")) {
        // Animate In - Overlay
        overlay.classList.replace("overlay-slide-left", "overlay-slide-right");

        // Animate In - Nav Items
        navAnimation("out", "in");
    } else {
        // Animate Out - Overlay
        overlay.classList.replace("overlay-slide-right", "overlay-slide-left");

        // Animate Out - Nav Items
        navAnimation("in", "out");
    }
}

// Events Listeners
hamburgerMenu.addEventListener("click", toggleNav);
navItems.forEach((nav) => {
    nav.addEventListener("click", toggleNav);
});