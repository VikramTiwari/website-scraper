// Remove invisible elements
function removeInvisibleElements() {
    const elements = document.querySelectorAll('*');
    elements.forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || 
            style.visibility === 'hidden' || 
            style.opacity === '0' ||
            el.offsetWidth === 0 ||
            el.offsetHeight === 0) {
            el.remove();
        }
    });
}

// Remove script and style tags
function removeScriptAndStyleTags() {
    document.querySelectorAll('script, style').forEach(el => el.remove());
}

// Remove empty nodes
function removeEmptyNodes() {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_ELEMENT,
        {
            acceptNode: function(node) {
                return node.children.length === 0 && 
                       !node.textContent.trim() ? 
                       NodeFilter.FILTER_ACCEPT : 
                       NodeFilter.FILTER_SKIP;
            }
        }
    );
    
    let node;
    while (node = walker.nextNode()) {
        node.remove();
    }
}

// Remove comment nodes
function removeCommentNodes() {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_COMMENT,
        null,
        false
    );
    
    let node;
    while (node = walker.nextNode()) {
        node.remove();
    }
}

// Clean up the page
function cleanPage() {
    // Basic cleanup
    removeInvisibleElements();
    removeScriptAndStyleTags();
    removeEmptyNodes();
    removeCommentNodes();
}
