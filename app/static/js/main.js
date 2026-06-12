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
      <circle cx="635" cy="118" r="118" fill="#E65100" fill-opacity="0.14"/>
      <rect x="178" y="124" width="444" height="232" rx="26" fill="#2A2A2A" stroke="#444444" stroke-width="3"/>
      <path d="M292 292l82-96 113 122H248z" fill="#E65100"/>
      <circle cx="289" cy="206" r="27" fill="#8B1E1E"/>
      <path d="M350 174h144M350 204h110M350 234h132" stroke="#BDBDBD" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
    </svg>
    `)}`;

    document.querySelectorAll("img[data-fallback='placeholder']").forEach((img) => {
      img.addEventListener("error", () => {
        img.src = placeholderSvg;
        img.alt = "بدون تصویر";
      });
    });

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (event) => {
        const href = anchor.getAttribute("href");
        if (!href || href === "#") return;

        const target = document.querySelector(href);
        if (target) {
          // Target exists on current page — scroll to it
          event.preventDefault();
          target.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
          return;
        }

        // Target does NOT exist on this page (e.g., nav links on blog_detail)
        // Redirect to homepage + hash instead of doing nothing
        const currentPath = window.location.pathname;
        if (currentPath !== "/" && currentPath !== "/index.html") {
          event.preventDefault();
          window.location.href = href;
        }
      });
    });
});
