const actionButtons = Array.from(document.querySelectorAll('.action-btn'));

function setupActionButtons() {
  actionButtons.forEach((button) => {
    button.addEventListener('click', (event) => {
      const id = event.currentTarget.id || event.currentTarget.textContent.trim();
      console.log(`Action button clicked: ${id}`);
    });
  });
}

window.addEventListener('DOMContentLoaded', setupActionButtons);
