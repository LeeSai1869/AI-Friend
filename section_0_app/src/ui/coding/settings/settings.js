export function createCodingSettings() {
  const button = document.getElementById("btn-settings");

  button?.addEventListener("click", () => {
    console.log("[coding/settings] settings requested");
  });

  return {};
}
