import React, { useState, useEffect, useCallback } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ChatInterface } from "./components/ChatInterface";
import { Sidebar } from "./components/Sidebar";
import { ContractPreview } from "./components/ContractPreview";
import { Auth } from "./components/Auth";
import { ForgotPassword } from "./components/ForgotPassword";
import { ResetPassword } from "./components/ResetPassword";
import { AuthProvider, useAuth } from "./contexts/AuthContext";

import {
  getChatHistory,
  getChatDetail,
  sendChatMessageStreaming,
} from "./services/apiService";

import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

// -------------------------------
// Helper
// -------------------------------
const isContractReady = (chat) => {
  if (!chat) return false;
  if (chat.contrato !== null && chat.contrato !== undefined) return true;
  if (chat.metadatos?.estado === "esperando_aprobacion_formal") return true;
  return false;
};

// -------------------------------
// CARGA INICIAL
// -------------------------------
function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen bg-slate-100">
      <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

// -------------------------------
// Main Authentication Gate
// -------------------------------
function MainApp() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingScreen />;
  return (
    <Router>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/*" element={isAuthenticated ? <ChatApp /> : <Auth />} />
      </Routes>
    </Router>
  );
}

// -------------------------------
// Chat Application
// -------------------------------
function ChatApp() {
  const { apiKey } = useAuth();
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [showContractPreview, setShowContractPreview] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 1024);

  const currentChat = chats.find((c) => c.id === activeChatId);

  const contexto = {
    estado: currentChat?.estado ?? null,
    respuestas: currentChat?.respuestas ?? {},
    tipo_contrato: currentChat?.tipoContrato ?? null,
    clausulas_especiales: currentChat?.clausulasEspeciales ?? [],
  };

  // -------------------------------
  // Load chat history
  // -------------------------------
  const loadHistory = useCallback(async () => {
    if (!apiKey) return;

    try {
      const history = await getChatHistory(apiKey);

      const loadedChats = history.map((item) => ({
        id: `chat-${item.chat_id}`,
        title: item.nombre,
        messages: [],
        contractGenerated: isContractReady(item),
        lastMessage: item.ultimo_mensaje,
        apiChatId: item.chat_id,
        contexto: item.metadatos || {},
      }));

      setChats(loadedChats);
    } catch (error) {
      toast.error("Error al cargar historial: " + error.message);
    }
  }, [apiKey]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // -------------------------------
  // Select chat and load its messages
  // -------------------------------
  const handleSelectChat = async (chatId) => {
    setActiveChatId(chatId);
    const chat = chats.find((c) => c.id === chatId);

    if (chat && isContractReady(chat)) {
      setShowContractPreview(true);
    } else if (chat) {
      setShowContractPreview(false);
    }

    if (!chat?.apiChatId || !apiKey || chat.messages.length > 0) return;

    try {
      const detail = await getChatDetail(chat.apiChatId, apiKey);

      const messages = detail.mensajes.map((msg) => ({
        id: `msg-${msg.id}`,
        role: msg.remitente === "usuario" ? "user" : "assistant",
        content: msg.contenido,
        createdAt: new Date(msg.fecha_creacion),
      }));

      const updatedChat = {
        ...chat,
        messages,
        contexto: detail.chat.metadatos,
        contractGenerated: isContractReady(detail.chat),
      };

      setChats((prev) => prev.map((c) => (c.id === chatId ? updatedChat : c)));

      if (isContractReady(updatedChat)) {
        setShowContractPreview(true);
      }
    } catch (error) {
      toast.error("Error al cargar conversación: " + error.message);
    }
  };

  // -------------------------------
  // New chat
  // -------------------------------
  const handleNewChat = () => {
    const newChat = {
      id: `new-${Date.now()}`,
      title: "Notar.IA",
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "Bienvenido. ¿Qué contrato necesita?",
          createdAt: new Date(),
        },
      ],
      contractGenerated: false,
      contexto: {},
    };

    setChats([newChat, ...chats]);
    setActiveChatId(newChat.id);
    setShowContractPreview(false);
  };

  // -------------------------------
  // Send Message (STREAMING)
  // -------------------------------
  const handleSendMessage = async (content) => {
    if (!currentChat) return;

    const userMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content,
      createdAt: new Date(),
    };

    setChats((prev) =>
      prev.map((chat) =>
        chat.id === activeChatId
          ? { ...chat, messages: [...chat.messages, userMessage] }
          : chat
      )
    );

    const assistantMessageId = `${Date.now()}-ai`;

    try {
      const contexto = {
        estado: currentChat.estado,
        respuestas: currentChat.respuestas,
        tipo_contrato: currentChat.tipoContrato,
        clausulas_especiales: currentChat.clausulasEspeciales,
      };

      await sendChatMessageStreaming(
        currentChat.apiChatId,
        content,
        apiKey,
        "Usuario",
        contexto,
        (chunk) => {
          let shouldOpenPreview = false;
          let updatedContext = null;

          if (chunk.context) {
            updatedContext = chunk.context;

            if (updatedContext.estado === "esperando_aprobacion_formal") {
              shouldOpenPreview = true;
            }
          }

          setChats((prev) =>
            prev.map((chat) => {
              if (chat.id !== activeChatId) return chat;

              let newMessages = [...chat.messages];
              let newContext = chat.contexto;
              let contractGenerated = chat.contractGenerated;

              if (chunk.text) {
                const last = newMessages[newMessages.length - 1];

                if (last?.id === assistantMessageId) {
                  last.content += chunk.text;
                } else {
                  newMessages.push({
                    id: assistantMessageId,
                    role: "assistant",
                    content: chunk.text,
                    createdAt: new Date(),
                  });
                }
              }

              if (updatedContext) {
                newContext = updatedContext;

                if (updatedContext.estado === "esperando_aprobacion_formal") {
                  contractGenerated = true;
                }
              }

              return {
                ...chat,
                messages: newMessages,
                contexto: newContext,
                contractGenerated,
              };
            })
          );

          if (shouldOpenPreview) {
            setShowContractPreview(true);
          }
        }
      );
    } catch (error) {
      toast.error(
        "Error en la comunicación con el asistente: " + error.message
      );
    }
  };

  // -------------------------------
  // UI Rendering
  // -------------------------------
  return (
    <div className="flex h-screen bg-slate-100 text-slate-800">
      <Sidebar
        chats={chats}
        activeChat={activeChatId || ""}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0">
          <ChatInterface
            chat={currentChat}
            onSendMessage={handleSendMessage}
            onTogglePreview={() => setShowContractPreview(!showContractPreview)}
            showPreview={showContractPreview}
          />
        </div>

        {showContractPreview && currentChat?.contractGenerated && (
          <div className="hidden lg:flex flex-col lg:w-1/2 xl:w-2/5 border-l border-slate-200">
            <ContractPreview
              chat={currentChat}
              onClose={() => setShowContractPreview(false)}
            />
          </div>
        )}
      </main>
    </div>
  );
}

// -------------------------------
export default function App() {
  return (
    <AuthProvider>
      <MainApp />
      <Toaster />
    </AuthProvider>
  );
}
