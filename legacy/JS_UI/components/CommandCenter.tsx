
import React, { useState, useRef, useCallback } from 'react';
import { Send, Mic, Sparkles, Loader2, X, Volume2, MicOff, AudioLines, AlertCircle, Languages, Phone, PhoneCall, Activity, DollarSign, ClipboardList } from 'lucide-react';
import { orchestrateInput } from '../services/gemini';
import { GoogleGenAI, Modality, Type } from '@google/genai';

interface CommandCenterProps {
  onProcessed: (result: any) => void;
  inventory: any[];
  orders: any[];
  financials: any[];
  onUpdateOrder?: (id: string, status: any) => void;
  voiceName?: string;
  language?: string;
}

// Audio Utilities for Live API
function encode(bytes: Uint8Array) {
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function decode(base64: string) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);
  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({ 
  onProcessed, 
  inventory, 
  orders,
  financials,
  onUpdateOrder,
  voiceName = 'Puck', 
  language = 'English' 
}) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);

  // Live API Refs
  const sessionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  const stopVoiceSession = useCallback(() => {
    if (sessionRef.current) {
      sessionRef.current.close();
      sessionRef.current = null;
    }
    if (sourcesRef.current) {
      sourcesRef.current.forEach(s => {
        try { s.stop(); } catch(e) {}
      });
      sourcesRef.current.clear();
    }
    setIsVoiceActive(false);
    setAgentSpeaking(false);
  }, []);

  const startVoiceSession = async () => {
    setError(null);
    try {
      setLoading(true);
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      
      const inputCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const outputCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      audioContextRef.current = outputCtx;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-09-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: voiceName as any } } },
          systemInstruction: `You are the Operational Brain of a restaurant. 
          Available Inventory: ${JSON.stringify(inventory)}.
          Current Orders: ${JSON.stringify(orders.slice(0, 10))}.
          Financial Summary: Total Revenue $${financials.reduce((sum, f) => sum + (f.type === 'INCOME' ? f.amount : -f.amount), 0).toFixed(2)}.
          
          MULTILINGUAL CAPABILITY: 
          - Primary Language Settings: ${language}.
          - You support Telugu (తెలుగు), Hindi, and English.
          - Respond in the language the user speaks to you. 
          
          You can place orders, check stock, update order status, and provide financial reports. Use the provided tools for actions. 
          Be concise, professional, and efficient.`,
          tools: [{
            functionDeclarations: [
              {
                name: 'placeOrder',
                description: 'Place a new order for food or drinks.',
                parameters: {
                  type: Type.OBJECT,
                  properties: {
                    items: {
                      type: Type.ARRAY,
                      items: {
                        type: Type.OBJECT,
                        properties: {
                          name: { type: Type.STRING },
                          quantity: { type: Type.NUMBER }
                        }
                      }
                    },
                    tableNumber: { type: Type.STRING }
                  },
                  required: ['items']
                }
              },
              {
                name: 'checkInventory',
                description: 'Check the current stock of an item.',
                parameters: {
                  type: Type.OBJECT,
                  properties: { itemName: { type: Type.STRING } },
                  required: ['itemName']
                }
              },
              {
                name: 'updateOrderStatus',
                description: 'Update the status of an existing order.',
                parameters: {
                  type: Type.OBJECT,
                  properties: { 
                    orderId: { type: Type.STRING },
                    status: { type: Type.STRING, enum: ['PREPARING', 'READY', 'SERVED', 'CANCELLED'] }
                  },
                  required: ['orderId', 'status']
                }
              },
              {
                name: 'getFinancialReport',
                description: 'Get a summary of recent financial transactions.',
                parameters: {
                  type: Type.OBJECT,
                  properties: { period: { type: Type.STRING, enum: ['today', 'recent'] } }
                }
              }
            ]
          }]
        },
        callbacks: {
          onopen: () => {
            setIsVoiceActive(true);
            setLoading(false);
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            scriptProcessor.onaudioprocess = (e) => {
              const inputData = e.inputBuffer.getChannelData(0);
              const int16 = new Int16Array(inputData.length);
              for (let i = 0; i < inputData.length; i++) int16[i] = inputData[i] * 32768;
              const pcmBlob = { data: encode(new Uint8Array(int16.buffer)), mimeType: 'audio/pcm;rate=16000' };
              sessionPromise.then(s => s.sendRealtimeInput({ media: pcmBlob }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: async (msg: any) => {
            const audioData = msg.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (audioData) {
              setAgentSpeaking(true);
              const buffer = await decodeAudioData(decode(audioData), outputCtx, 24000, 1);
              const source = outputCtx.createBufferSource();
              source.buffer = buffer;
              source.connect(outputCtx.destination);
              const startAt = Math.max(nextStartTimeRef.current, outputCtx.currentTime);
              source.start(startAt);
              nextStartTimeRef.current = startAt + buffer.duration;
              sourcesRef.current.add(source);
              source.onended = () => {
                sourcesRef.current.delete(source);
                if (sourcesRef.current.size === 0) setAgentSpeaking(false);
              };
            }

            if (msg.toolCall) {
              const functionResponses: any[] = [];
              for (const fc of msg.toolCall.functionCalls) {
                if (fc.name === 'placeOrder') {
                  onProcessed({
                    intent: 'ORDER',
                    data: fc.args,
                    agentResponse: `Placed order for ${fc.args.items.map((i: any) => i.name).join(', ')}.`
                  });
                  functionResponses.push({ id: fc.id, name: fc.name, response: { result: "Order placed successfully" } });
                } else if (fc.name === 'checkInventory') {
                  const item = inventory.find(i => i.name.toLowerCase().includes(fc.args.itemName.toLowerCase()));
                  const response = item 
                    ? { result: `${item.name} has ${item.quantity} ${item.unit} in stock.` } 
                    : { result: "Item not found in inventory." };
                  functionResponses.push({ id: fc.id, name: fc.name, response });
                } else if (fc.name === 'updateOrderStatus') {
                  if (onUpdateOrder) {
                    onUpdateOrder(fc.args.orderId, fc.args.status);
                    functionResponses.push({ id: fc.id, name: fc.name, response: { result: `Order ${fc.args.orderId} updated to ${fc.args.status}` } });
                  } else {
                    functionResponses.push({ id: fc.id, name: fc.name, response: { result: "Order update not available in this context." } });
                  }
                } else if (fc.name === 'getFinancialReport') {
                  const total = financials.reduce((sum, f) => sum + (f.type === 'INCOME' ? f.amount : -f.amount), 0);
                  functionResponses.push({ id: fc.id, name: fc.name, response: { result: `Total balance is $${total.toFixed(2)}. There are ${financials.length} recent transactions.` } });
                }
              }
              if (functionResponses.length > 0) {
                sessionPromise.then(s => s.sendToolResponse({ functionResponses }));
              }
            }

            if (msg.serverContent?.interrupted) {
              sourcesRef.current.forEach(s => { try { s.stop(); } catch(e) {} });
              sourcesRef.current.clear();
              nextStartTimeRef.current = 0;
            }
          },
          onclose: () => stopVoiceSession(),
          onerror: (e) => { 
            console.error(e); 
            setError("Voice connection error.");
            stopVoiceSession(); 
          }
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (err: any) {
      setError(err?.message || "Failed to start voice session.");
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await orchestrateInput(input, inventory);
      onProcessed(result);
      setInput('');
    } catch (err: any) {
      console.error("Agent failed to process:", err);
      setError("Operation failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      <div className="glass-panel rounded-2xl p-6 shadow-xl border-t border-white/10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-emerald-600/20 rounded-xl flex items-center justify-center border border-emerald-500/30">
              <Sparkles className="text-emerald-400" size={24} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white leading-tight">Operational Brain</h3>
              <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-widest font-black">
                <Activity size={10} className="text-emerald-500" />
                <span>System Online</span>
                <span className="mx-1">•</span>
                <Languages size={10} />
                <span>{language} Enabled</span>
              </div>
            </div>
          </div>
          
          <button
            onClick={isVoiceActive ? stopVoiceSession : startVoiceSession}
            disabled={loading && !isVoiceActive}
            className={`flex items-center gap-3 px-6 py-3 rounded-xl font-bold transition-all shadow-lg ${
              isVoiceActive 
                ? 'bg-red-600 text-white animate-pulse shadow-red-900/20' 
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20'
            }`}
          >
            {loading && !isVoiceActive ? (
              <Loader2 size={20} className="animate-spin" />
            ) : isVoiceActive ? (
              <PhoneCall size={20} />
            ) : (
              <Phone size={20} />
            )}
            <span>{isVoiceActive ? 'End Call' : 'Call Agent'}</span>
          </button>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 text-red-400 text-xs font-medium bg-red-400/10 p-3 rounded-xl border border-red-400/20">
            <AlertCircle size={14} />
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="relative">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isVoiceActive}
            placeholder={isVoiceActive ? "Voice session active..." : "Type a command or use the Call button..."}
            className={`w-full bg-zinc-900/50 border rounded-xl py-4 pl-4 pr-16 focus:ring-2 focus:outline-none text-white transition-all disabled:opacity-50 ${error ? 'border-red-500/50 focus:ring-red-500/30' : 'border-zinc-700 focus:ring-emerald-500/50'}`}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            <button
              type="submit"
              disabled={loading || isVoiceActive}
              className="p-2 bg-zinc-800 hover:bg-zinc-700 text-emerald-500 rounded-lg transition-all disabled:opacity-50"
            >
              <Send size={20} />
            </button>
          </div>
        </form>
        
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          {['Place 2 Dosa Table 3', 'Stock status?', 'Recent Revenue'].map(tip => (
            <button
              key={tip}
              onClick={() => {
                setInput(tip);
                setError(null);
              }}
              disabled={isVoiceActive}
              className="text-[10px] bg-zinc-800 hover:bg-zinc-700 text-zinc-500 hover:text-zinc-300 py-1 px-3 rounded-full border border-zinc-700 whitespace-nowrap transition-colors"
            >
              {tip}
            </button>
          ))}
        </div>
      </div>

      {isVoiceActive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="w-full max-w-lg glass-panel p-8 rounded-3xl border border-emerald-500/30 flex flex-col items-center gap-8 shadow-2xl shadow-emerald-500/10">
            <div className="flex justify-between w-full items-center mb-4">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-emerald-500 rounded-full animate-ping" />
                <span className="text-xs font-black tracking-widest text-emerald-500 uppercase">Live Multilingual Agent</span>
              </div>
              <button onClick={stopVoiceSession} className="p-2 bg-zinc-800 rounded-full hover:bg-zinc-700 transition-colors">
                <X size={20} />
              </button>
            </div>

            <div className="flex flex-col items-center gap-4">
              <div className={`w-32 h-32 rounded-full flex items-center justify-center border-4 transition-all duration-500 ${agentSpeaking ? 'border-emerald-500 bg-emerald-500/10 scale-110' : 'border-zinc-800 bg-zinc-900'}`}>
                {agentSpeaking ? <Volume2 size={48} className="text-emerald-500" /> : <AudioLines size={48} className="text-zinc-500" />}
              </div>
              <p className="text-xl font-bold">{agentSpeaking ? "Speaking..." : "Listening..."}</p>
            </div>

            <div className="w-full bg-zinc-900/50 p-6 rounded-2xl border border-zinc-800 min-h-[100px] flex items-center justify-center italic text-zinc-400 text-center">
              "Tell me to place an order..."
            </div>

            <button 
              onClick={stopVoiceSession}
              className="flex items-center gap-3 px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-black transition-all shadow-xl shadow-red-900/20 active:scale-95"
            >
              <MicOff size={20} /> END SESSION
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
