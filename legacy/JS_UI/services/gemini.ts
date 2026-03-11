
import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

/**
 * Utility function to execute API calls with exponential backoff retries.
 */
async function withRetry<T>(fn: () => Promise<T>, maxRetries = 3, initialDelay = 1000): Promise<T> {
  let lastError: any;
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;
      // Retry on 503 (Unavailable), 500 (Internal Error), or 429 (Rate Limit)
      const status = error?.error?.code || error?.status;
      if (status === 503 || status === 429 || status === 500) {
        const delay = initialDelay * Math.pow(2, i);
        console.warn(`Gemini API busy (Status ${status}). Retrying in ${delay}ms... (Attempt ${i + 1}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error; // Re-throw if it's a non-retryable error (e.g., 400 Bad Request)
    }
  }
  throw lastError;
}

export const orchestrateInput = async (input: string, currentInventory: any[]) => {
  return withRetry(async () => {
    const response = await ai.models.generateContent({
      model: "gemini-3.1-pro-preview",
      contents: `Act as the 'Operational Brain' for a high-performance restaurant.
      
Staff Input: "${input}"
Current Inventory State: ${JSON.stringify(currentInventory)}

Your tasks:
1. Identify the intent: ORDER, INVENTORY_CHECK, INVENTORY_UPDATE, or QUERY.
2. If it's an ORDER:
   - Extract items, quantities, and table number/type.
   - For each item, identify which specific inventory items are likely consumed.
   - Calculate suggested inventory deductions.
   
CRITICAL THRESHOLD MONITORING:
- For every inventory deduction, check if (currentQuantity - deductionAmount) is less than or equal to the minThreshold.
- If an item drops below or reaches its minThreshold, you MUST:
  a) Include a specific warning in the 'agentResponse' (e.g., "Order placed, but we are running critically low on [Item Name]").
  b) Add a clear, actionable string to the 'inventoryAlerts' array (e.g., "CRITICAL: [Item Name] is below threshold ([Value] [Unit] remaining)").
  c) If an item is completely depleted, suggest an alternative or state that the item might be unavailable for future orders.

3. Provide a concise, professional agentResponse.
4. Provide specific inventoryAlerts.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            intent: { type: Type.STRING },
            data: {
              type: Type.OBJECT,
              properties: {
                items: {
                  type: Type.ARRAY,
                  items: {
                    type: Type.OBJECT,
                    properties: {
                      name: { type: Type.STRING },
                      quantity: { type: Type.NUMBER },
                      price_estimated: { type: Type.NUMBER }
                    }
                  }
                },
                tableNumber: { type: Type.STRING },
                inventoryTarget: { type: Type.STRING },
                query: { type: Type.STRING }
              }
            },
            inventoryImpact: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  inventoryItemId: { type: Type.STRING },
                  ingredientName: { type: Type.STRING },
                  deductionAmount: { type: Type.NUMBER },
                  unit: { type: Type.STRING }
                },
                required: ["inventoryItemId", "deductionAmount"]
              }
            },
            agentResponse: { type: Type.STRING },
            inventoryAlerts: { type: Type.ARRAY, items: { type: Type.STRING } }
          },
          required: ["intent", "agentResponse"]
        }
      }
    });

    return JSON.parse(response.text);
  });
};
