// static/js/theme.js
(function() {
    const themeToggle = document.getElementById('theme-toggle');
    const rootElement = document.documentElement; // Target <html> tag

    // Function to sync the toggle checkbox state based on html class
    const syncToggleState = () => {
        if (themeToggle) {
            // Set checkbox state based on whether <html> has the dark-mode class
            themeToggle.checked = rootElement.classList.contains('dark-mode');
        }
    };

    // Ensure the toggle state is correct after the initial paint
    // (The head script sets the class, this syncs the checkbox)
    syncToggleState();

    // Add listener for toggle switch clicks/changes
    if (themeToggle) {
        themeToggle.addEventListener('change', function() {
            // Toggle class on <html> element
            rootElement.classList.toggle('dark-mode', this.checked);

            // Update localStorage preference
            localStorage.setItem('theme', this.checked ? 'dark' : 'light');
        });
    }

    // Optional: Listening for system changes is less critical now,
    // as the user preference in localStorage takes precedence.
    // You could add it back to automatically switch if the user *hasn't*
    // manually toggled the switch (i.e., localStorage is not set).

})();