/* Main Interactive JavaScript for Generated Websites */
document.addEventListener("DOMContentLoaded", function () {
  console.log("Generated website initialized.");

  // Mobile menu toggle logic
  const toggleBtn = document.querySelector(".menu-toggle");
  const nav = document.querySelector("nav");
  if (toggleBtn && nav) {
    toggleBtn.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }

  // FAQ Accordion logic
  const faqTitles = document.querySelectorAll(".faq-title");
  faqTitles.forEach(function (title) {
    title.addEventListener("click", function () {
      const parent = title.parentElement;
      parent.classList.toggle("active");
    });
  });
});
