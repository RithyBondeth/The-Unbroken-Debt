import { describe, expect, it } from "vitest";
import {
  TAXI_CONVERSATION,
  taxiConversationAt,
} from "../../src/episodes/ep1/travel/taxiConversation";
describe("taxi conversation", () => {
  it("gives both characters a readable exchange without overlapping lines or the final fade", () => {
    expect(TAXI_CONVERSATION.filter((l) => l.speaker === "Sora")).toHaveLength(7);
    expect(TAXI_CONVERSATION.filter((l) => l.speaker === "Driver")).toHaveLength(7);
    for (const [i, line] of TAXI_CONVERSATION.entries()) {
      expect(line.text.split(/\s+/).length / line.seconds).toBeLessThan(3);
      expect(line.at + line.seconds).toBeLessThanOrEqual(TAXI_CONVERSATION[i + 1]?.at ?? 70);
      expect(taxiConversationAt(line.at)?.text).toBe(line.text);
    }
    expect(taxiConversationAt(37.8)).toBeNull();
    expect(taxiConversationAt(71)).toBeNull();
  });
  it("restores the current reply on a mid-line save and selects directly after a hitch", () => {
    expect(taxiConversationAt(32)?.speaker).toBe("Driver");
    expect(taxiConversationAt(32)?.text).toContain("weather");
    expect(taxiConversationAt(46)?.text).toContain("eyes forward");
    expect(taxiConversationAt(50)?.speaker).toBe("Sora");
    expect(taxiConversationAt(60)?.text).toContain("house");
    expect(taxiConversationAt(69.5)).toBeNull();
  });
});
