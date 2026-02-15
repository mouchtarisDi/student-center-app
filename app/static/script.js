// Modal (Students page)
(function () {
  const modal = document.getElementById("studentModal");
  if (!modal) return;

  const closeBtn = document.getElementById("modalCloseBtn");

  const nameEl = document.getElementById("modalStudentName");
  const metaEl = document.getElementById("modalStudentMeta");
  const centerEl = document.getElementById("modalCenter");
  const parentEl = document.getElementById("modalParent");
  const phoneEl = document.getElementById("modalPhone");
  const dobEl = document.getElementById("modalDob");
  const expEl = document.getElementById("modalExp");

  const deleteForm = document.getElementById("deleteStudentForm");
  const openLink = document.getElementById("openStudentLink");

  function openModal() {
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }
  function closeModal() {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  }

  closeBtn?.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  document.querySelectorAll(".student-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      const amka = btn.dataset.studentAmka || "";
      const name = btn.dataset.studentName || "Μαθητής";
      const center = btn.dataset.studentCenter || "-";
      const parent = btn.dataset.studentParent || "-";
      const phone = btn.dataset.studentPhone || "-";
      const dob = btn.dataset.studentDob || "-";
      const exp = btn.dataset.studentExp || "-";

      nameEl.textContent = name;
      metaEl.textContent = `AMKA: ${amka}`;
      centerEl.textContent = center;
      parentEl.textContent = parent || "-";
      phoneEl.textContent = phone || "-";
      dobEl.textContent = dob;
      expEl.textContent = exp;

      deleteForm.setAttribute("action", `/students/${amka}/delete`);
      openLink.setAttribute("href", `/students/${amka}`);

      openModal();
    });
  });
})();


// Tabs (Student page)
(function () {
  const tabs = document.querySelectorAll(".tab");
  if (!tabs.length) return;

  const panes = document.querySelectorAll(".tab-pane");

  function activate(id) {
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === id));
    panes.forEach((p) => p.classList.toggle("active", p.id === id));
  }

  tabs.forEach((t) => {
    t.addEventListener("click", () => activate(t.dataset.tab));
  });
})();
