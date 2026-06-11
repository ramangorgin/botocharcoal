document.addEventListener("DOMContentLoaded", () => {
  const preloader = document.getElementById("preloader");
  const menuToggle = document.querySelector("[data-menu-toggle]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");

  const hidePreloader = () => {
    if (!preloader) return;
    preloader.classList.add("is-hidden");
    setTimeout(() => {
      preloader.style.display = "none";
    }, 500);
  };

  window.addEventListener("load", hidePreloader);
  setTimeout(hidePreloader, 1800);

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener("click", () => {
      const isOpen = mobileMenu.classList.toggle("is-open");
      menuToggle.classList.toggle("is-active", isOpen);
      menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    mobileMenu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        mobileMenu.classList.remove("is-open");
        menuToggle.classList.remove("is-active");
        menuToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  const revealElements = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, {
      threshold: 0.14,
      rootMargin: "0px 0px -40px 0px"
    });

    revealElements.forEach((element) => revealObserver.observe(element));
  } else {
    revealElements.forEach((element) => element.classList.add("is-visible"));
  }

  const placeholderSvg = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
    <defs>
    <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0%" stop-color="#242424"/>
    <stop offset="100%" stop-color="#333333"/>
    </linearGradient>
    </defs>
    <rect width="800" height="500" fill="url(#g)"/>
    <circle cx="640" cy="120" r="120" fill="rgba(230,81,0,0.16)"/>
    <rect x="170" y="120" width="460" height="240" rx="28" fill="#2A2A2A" stroke="#444444" stroke-width="3"/>
    <circle cx="280" cy="205" r="28" fill="#8B1E1E"/>
    <path d="M330 300l88-102 120 128H250z" fill="#E65100"/>
    <text x="400" y="410" text-anchor="middle" fill="#BDBDBD" font-size="28" font-family="Arial, sans-serif">
    No image available
    </text>
    </svg>
    `)}`;

    document.querySelectorAll("img[data-fallback='placeholder']").forEach((img) => {
      img.addEventListener("error", () => {
        img.src = placeholderSvg;
        img.alt = "No image available";
      });
    });

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (event) => {
        const href = anchor.getAttribute("href");
        if (!href || href === "#") return;

        const target = document.querySelector(href);
        if (!target) return;

        event.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      });
    });
});
