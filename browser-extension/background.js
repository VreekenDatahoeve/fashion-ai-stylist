const APP_URL = "https://fashion-ai-stylis-ifidobqmkgjtn7gjxgrudb.streamlit.app";

async function openInStylist(tab) {
  if (!tab || !tab.url) return;
  const target = `${APP_URL}?u=${encodeURIComponent(tab.url)}&auto=1`;
  chrome.tabs.create({ url: target });
}

chrome.action.onClicked.addListener(openInStylist);

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "open-stylist",
    title: "Open in Fashion AI Stylist",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "open-stylist") openInStylist(tab);
});
