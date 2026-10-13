// Keep this small and dependency-free.

// Client-side publication filter (search across title, venue, authors).
(function () {
  const input = document.getElementById("pubFilter");
  if (!input) return;
  const entries = Array.from(document.querySelectorAll(".entry"));

  function norm(s) {
    return (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  input.addEventListener("input", function () {
    const q = norm(input.value.trim());
    let shown = 0;
    entries.forEach(function (el) {
      const hay = norm(el.textContent);
      const match = !q || hay.indexOf(q) !== -1;
      el.classList.toggle("hidden", !match);
      if (match) shown++;
    });
    // Hide year headers that no longer have a visible entry beneath them.
    document.querySelectorAll(".pub-year").forEach(function (h) {
      let sibling = h.nextElementSibling;
      let any = false;
      while (sibling && sibling.classList.contains("entry")) {
        if (!sibling.classList.contains("hidden")) { any = true; break; }
        sibling = sibling.nextElementSibling;
      }
      h.classList.toggle("hidden", !any);
    });
    const count = document.getElementById("pubCount");
    if (count) count.textContent = shown + " of " + entries.length;
  });
})();
