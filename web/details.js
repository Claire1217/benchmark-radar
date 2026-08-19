(function () {
  function addStructuredDetails() {
    if (!window.benchmarkRadarState || !Array.isArray(window.benchmarkRadarState.benchmarks)) return;
    document.querySelectorAll(".benchmark-card:not([data-details-hydrated])").forEach((card) => {
      card.dataset.detailsHydrated = "true";
      const record = window.benchmarkRadarState.benchmarks.find((item) => item.id === card.dataset.id);
      const panel = card.querySelector(".details-panel");
      if (!record || !panel) return;

      if (record.constructionDetail && !record.constructionDetail.startsWith("Unknown")) {
        const copy = document.createElement("p");
        copy.className = "curated-copy";
        copy.textContent = record.constructionDetail;
        panel.insertBefore(copy, panel.querySelector(".evidence"));
      }

      if (record.metrics?.length) {
        const design = document.createElement("div");
        design.className = "benchmark-design";
        const heading = document.createElement("h3");
        heading.textContent = "Benchmark design";
        const grid = document.createElement("div");
        record.metrics.forEach((metric) => {
          const item = document.createElement("section");
          const label = document.createElement("span");
          const value = document.createElement("strong");
          label.textContent = metric.name;
          value.textContent = metric.value;
          item.append(label, value);
          if (metric.note) {
            const note = document.createElement("small");
            note.textContent = metric.note;
            item.append(note);
          }
          grid.append(item);
        });
        design.append(heading, grid);
        panel.insertBefore(design, panel.querySelector(".evidence"));
      }
    });
  }

  const observer = new MutationObserver(addStructuredDetails);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  addStructuredDetails();
})();
