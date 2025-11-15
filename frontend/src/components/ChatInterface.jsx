import React, { useState, useRef, useEffect } from "react";
import { Send, FileText, Loader2 } from "lucide-react";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { ChatMessage } from "./ChatMessage";

export function ChatInterface({
  chat,
  onSendMessage,
  onTogglePreview,
  showPreview,
}) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat?.messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (input.trim() && !isSending) {
      setIsSending(true);
      await onSendMessage(input.trim());
      setInput("");
      setIsSending(false);
    }
  };

  // Render a placeholder if no chat is active
  if (!chat) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center bg-slate-50">
        <FileText className="h-16 w-16 text-slate-300" />
        <h2 className="mt-4 text-xl font-semibold text-slate-600">
          Bienvenido a tu Asistente Notarial
        </h2>
        <p className="mt-2 text-slate-500">
          Selecciona una conversación o crea un nuevo contrato para comenzar.
        </p>
      </div>
    );
  }

  const { title, messages, contractGenerated } = chat;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 p-4 bg-white">
        <div>
          <h2 className="font-semibold text-slate-800">{title}</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {contractGenerated ? (
              <span className="text-green-600 font-medium">
                ✓ Contrato generado
              </span>
            ) : (
              <span>Generando contrato...</span>
            )}
          </p>
        </div>
        {/* The button ONLY appears if a contract has been generated */}
        {contractGenerated && (
          <Button
            onClick={onTogglePreview}
            variant={showPreview ? "default" : "outline"}
            size="sm"
            className={`hidden lg:flex items-center gap-2 transition-all ${
              showPreview
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "border-slate-300 text-slate-600 hover:bg-slate-100 hover:text-slate-800"
            }`}
          >
            <FileText className="h-4 w-4" />
            {showPreview ? "Ocultar" : "Ver"} Preliminar
          </Button>
        )}
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="max-w-4xl mx-auto space-y-8 p-4 lg:p-6">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {isSending && <ChatMessage.Loading />}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Form */}
      <div className="border-t border-slate-200 p-4 bg-white/80 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                isSending
                  ? "Esperando respuesta..."
                  : "Describa el contrato que necesita o responda..."
              }
              className="flex-1 px-4 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white disabled:bg-slate-100"
              disabled={isSending}
            />
            <Button
              type="submit"
              disabled={!input.trim() || isSending}
              className="bg-blue-600 hover:bg-blue-700 text-white px-5 rounded-lg"
              size="icon"
            >
              {isSending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
