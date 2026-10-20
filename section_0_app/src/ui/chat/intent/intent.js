import {
  getIntent,
  render as renderSharedIntent,
} from "../../../intents.js";

export function createChatIntent() {
  renderSharedIntent();

  return {
    getIntent,
  };
}
