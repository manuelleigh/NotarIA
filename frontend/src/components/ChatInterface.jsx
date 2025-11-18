import React, { useState, useRef, useEffect } from "react";
import { Send, FileText, Loader2 } from "lucide-react";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { ChatMessage } from "./ChatMessage";
import SignersModal from "./SignersModal";

const ROLE_KEYS = [
  "arrendador",
  "arrendatario",
  "prestador",
  "cliente",
  "vendedor",
  "comprador",
  "comodante",
  "comodatario",
  "mutuante",
  "mutuario",
  "deudor",
  "acreedor",
  "empleador",
  "trabajador",
  "poderdante",
  "apoderado",
  "franquiciante",
  "franquiciado",
  "anunciante",
  "publicista",
  "asociante",
  "asociado",
];

function parsePersona(texto = "") {
  if (!texto) return { nombre: "", dni: "" };
  const dniMatch = texto.match(/\b(\d{8})\b/);
  const dni = dniMatch ? dniMatch[0] : "";
  let nombre = texto.replace(dni, "");
  nombre = nombre.split(/,| y | con domicilio/i)[0].trim();
  return { nombre, dni };
}

function getDefaultSigners(contexto) {
  if (!contexto?.respuestas) return [];

  const signers = [];

  ROLE_KEYS.forEach((role) => {
    const raw = contexto.respuestas[role];
    if (raw) {
      signers.push({
        role,
        ...parsePersona(raw),
        correo: "",
        telefono: "",
      });
    }
  });

  return signers;
}

export function ChatInterface({
  chat,
  onSendMessage,
  onTogglePreview,
  showPreview,
}) {
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [typingIndicator, setTypingIndicator] = useState(false);
  const [isSignersModalOpen, setIsSignersModalOpen] = useState(false);

  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const animatedPlaceholder = [
    "Escribe aquí tu consulta…",
    "Por ejemplo: necesito un contrato de alquiler…",
    "Describe el contrato que necesitas…",
  ];

  const [placeholderText, setPlaceholderText] = useState(
    animatedPlaceholder[0]
  );
  const placeholderIndex = useRef(0);

  useEffect(() => {
    const interval = setInterval(() => {
      placeholderIndex.current =
        (placeholderIndex.current + 1) % animatedPlaceholder.length;
      setPlaceholderText(animatedPlaceholder[placeholderIndex.current]);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [chat?.messages]);
  useEffect(() => {
    if (typingIndicator) scrollToBottom();
  }, [typingIndicator]);

  const handleSignersConfirm = async (signers) => {
    setIsSignersModalOpen(false);

    const message = `Okay, procede a generar el contrato con estos firmantes: ${JSON.stringify(
      signers,
      null,
      2
    )}`;

    setIsSending(true);
    setTypingIndicator(true);
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    await onSendMessage(message);

    setTypingIndicator(false);
    setIsSending(false);

    setTimeout(() => {
      inputRef.current?.focus();
    }, 30);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;

    const text = input.trim();

    const affirmativeKeywords = [
      "si",
      "sí",
      "ok",
      "dale",
      "procede",
      "continua",
      "generalo",
      "genéralo",
      "acepto",
      "confirmar",
    ];

    const textNormalized = text.toLowerCase().replace(/[.,!]/g, "");
    const isAffirmative = affirmativeKeywords.some((keyword) =>
      textNormalized.includes(keyword)
    );

    // 🚀 NUEVA LÓGICA
    const isPreliminar =
      chat?.estado === "esperando_aprobacion_formal" ||
      chat?.estado === "generando_contrato" ||
      chat?.estado === "formalizado";

    if (isPreliminar && isAffirmative) {
      setInput("");
      setIsSignersModalOpen(true);
      return;
    }

    setInput("");
    setIsSending(true);
    setTypingIndicator(true);

    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    await onSendMessage(text);

    setTypingIndicator(false);
    setIsSending(false);

    setTimeout(() => {
      inputRef.current?.focus();
    }, 30);
  };

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

  const { title, messages, contractGenerated, contexto } = chat;

  const getStatusDisplay = () => {
    if (!contractGenerated) {
      return {
        text: "Asistente legal con IA",
        className: "text-slate-500",
        buttonText: "",
      };
    }

    switch (contexto?.estado) {
      case "esperando_aprobacion_formal":
        return {
          text: "Contrato Preliminar Disponible",
          className: "text-blue-600 font-medium",
          buttonText: "Ver Preliminar",
        };
      case "formalizado":
        return {
          text: "Contrato Formalizado",
          className: "text-green-600 font-medium",
          buttonText: "Ver Formalizado",
        };
      default:
        return {
          text: "Contrato Disponible",
          className: "text-green-600 font-medium",
          buttonText: "Ver Contrato",
        };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <SignersModal
        open={isSignersModalOpen}
        onOpenChange={setIsSignersModalOpen}
        defaultSigners={getDefaultSigners(chat.contexto)}
        onConfirm={handleSignersConfirm}
      />

      <div className="flex items-center justify-between border-b border-slate-200 p-4 bg-white">
        <div>
          <h2 className="font-semibold text-slate-800">{title}</h2>
          <p className="text-sm mt-0.5">
            <span className={statusDisplay.className}>
              {statusDisplay.text}
            </span>
          </p>
        </div>

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
            {showPreview ? "Ocultar" : statusDisplay.buttonText}
          </Button>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6 max-w-4xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}

          {typingIndicator && (
            <div className="flex items-start gap-3 animate-pulse text-slate-500">
              <div className="w-6 h-6 rounded-full bg-slate-300"></div>
              <div className="flex space-x-2 p-3">
                <div className="w-3 h-3 bg-slate-300 rounded-full"></div>
                <div className="w-3 h-3 bg-slate-300 rounded-full"></div>
                <div className="w-3 h-3 bg-slate-300 rounded-full"></div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <div className="border-t border-slate-200 p-4 bg-white/80 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-2 items-end">
            <textarea
              ref={inputRef}
              value={input}
              placeholder={
                isSending ? "El asistente está escribiendo..." : placeholderText
              }
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = e.target.scrollHeight + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={isSending}
              className="flex-1 px-4 py-2 rounded-lg border border-slate-300 focus:outline-none 
                         focus:ring-2 focus:ring-blue-600 bg-white disabled:bg-slate-100
                         resize-none overflow-hidden leading-6 min-h-[48px] max-h-[200px]"
            />

            <Button
              type="submit"
              disabled={!input.trim() || isSending}
              className="bg-blue-600 hover:bg-blue-700 text-white px-5 rounded-lg"
              size="icon"
              style={{ alignSelf: "flex-end" }}
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
