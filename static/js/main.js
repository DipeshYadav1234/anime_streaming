document.addEventListener("DOMContentLoaded", () => {

    let heroIndex = 0;

    function getSlides() {
        return document.querySelectorAll(".hero-slide");
    }

    function showHero(i) {
        const slides = getSlides();
        if (!slides.length) return;

        slides.forEach(s => s.classList.remove("active"));
        slides[i].classList.add("active");
    }

    function nextHero() {
        const slides = getSlides();
        if (!slides.length) return;

        heroIndex = (heroIndex + 1) % slides.length;
        showHero(heroIndex);
    }

    function prevHero() {
        const slides = getSlides();
        if (!slides.length) return;

        heroIndex = (heroIndex - 1 + slides.length) % slides.length;
        showHero(heroIndex);
    }

    // Auto slide ONLY if carousel exists
    if (getSlides().length) {
        setInterval(nextHero, 6000);
    }

    // expose for buttons
    window.nextHero = nextHero;
    window.prevHero = prevHero;
});
