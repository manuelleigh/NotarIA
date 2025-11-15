import React, { useState, useEffect, useCallback } from "react";
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ChatInterface } from "./components/ChatInterface";
import { Sidebar } from "./components/Sidebar";
import { ContractPreview } from "./components/ContractPreview";
import { Auth } from "./components/Auth";
import { ForgotPassword } from "./components/ForgotPassword";
import { ResetPassword } from "./components/ResetPassword";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { getChatHistory, getChatDetail, sendChatMessageStreaming } from "./services/apiService";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";

// --- Helper para determinar si el contrato está listo ---
const isContractReady = (chat) => {
  if (!chat) return false;
  // Condición 1: Ya hay un contrato guardado en la BD.
  if (chat.contrato !== null && chat.contrato !== undefined) return true;
  // Condición 2: El estado del chat indica que está listo para la vista previa.
  if (chat.metadatos?.estado === 'esperando_aprobacion_formal') return true;
  return false;
};

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen bg-slate-100">
      <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

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

function ChatApp() {
  const { apiKey } = useAuth();
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [showContractPreview, setShowContractPreview] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 1024);

  const currentChat = chats.find((chat) => chat.id === activeChatId);

  const loadHistory = useCallback(async () => {
    if (!apiKey) return;
    try {
      const history = await getChatHistory(apiKey);
      const loadedChats = history.map((item) => ({
        id: `chat-${item.chat_id}`,
        title: item.nombre,
        messages: [],
        // LÓGICA CORREGIDA AQUÍ
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

  const handleSelectChat = async (chatId) => {
    setActiveChatId(chatId);
    const chat = chats.find((c) => c.id === chatId);
    
    // Si el chat ya tiene el estado correcto, muestra la preview inmediatamente
    if (chat && isContractReady(chat)) {
        setShowContractPreview(true);
    }

    if (!chat?.apiChatId || !apiKey || (chat.messages && chat.messages.length > 0)) {
      return;
    }

    try {
      const detail = await getChatDetail(chat.apiChatId, apiKey);
      const messages = detail.mensajes.map((msg) => ({
        id: `msg-${msg.id}`,
        role: msg.remitente === "usuario" ? "user" : "assistant",
        content: msg.contenido,
        createdAt: new Date(msg.fecha_creacion),
      }));

      setChats((prev) =>
        prev.map((c) =>
          c.id === chatId
            ? { ...c, messages, contexto: detail.chat.metadatos, contractGenerated: isContractReady(detail.chat) }
            : c
        )
      );
      // LÓGICA CORREGIDA AQUÍ
      if (isContractReady(detail.chat)) {
        setShowContractPreview(true);
      }
    } catch (error) {
      toast.error("Error al cargar la conversación: " + error.message);
    }
  };

  const handleNewChat = () => {
    const newChat = {
      id: `new-${Date.now()}`,
      title: "Nuevo Contrato",
      messages: [
        { id: `msg-${Date.now()}`, role: "assistant", content: "Bienvenido. ¿Qué contrato necesita?", createdAt: new Date() },
      ],
      contractGenerated: false,
      contexto: {},
    };
    setChats([newChat, ...chats]);
    setActiveChatId(newChat.id);
    setShowContractPreview(false);
  };

  const handleSendMessage = async (content) => {
    if (!currentChat) return;

    const userMessage = { id: `${Date.now()}-user`, role: "user", content, createdAt: new Date() };
    const updatedMessages = [...currentChat.messages, userMessage];
    setChats((prev) => prev.map((chat) => (chat.id === activeChatId ? { ...chat, messages: updatedMessages } : chat)));

    const assistantMessageId = `${Date.now()}-ai`;
    try {
      await sendChatMessageStreaming(currentChat.contexto, content, (chunk) => {
        setChats((prev) => {
          return prev.map((chat) => {
            if (chat.id !== activeChatId) return chat;

            let newMessages = [...chat.messages];
            let newContext = chat.contexto;
            let contractGenerated = chat.contractGenerated;

            if (chunk.text) {
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.id === assistantMessageId) {
                newMessages[newMessages.length - 1] = { ...lastMessage, content: lastMessage.content + chunk.text };
              } else {
                newMessages.push({ id: assistantMessageId, role: "assistant", content: chunk.text, createdAt: new Date() });
              }
            }
            if (chunk.context) {
              newContext = chunk.context;
              // LÓGICA CORREGIDA AQUÍ (EN TIEMPO REAL)
              if (newContext.estado === 'esperando_aprobacion_formal') {
                  contractGenerated = true;
                  setShowContractPreview(true); // Abrir preview automáticamente
              }
            }

            return { ...chat, messages: newMessages, contexto: newContext, contractGenerated };
          });
        });
      });
    } catch (error) {
      toast.error("Error en la comunicación con el asistente: " + error.message);
    }
  };

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
      <main className="flex-1 flex flex-col overflow-hidden">
        <ChatInterface
          chat={currentChat}
          onSendMessage={handleSendMessage}
          onTogglePreview={() => setShowContractPreview(!showContractPreview)}
          showPreview={showContractPreview}
        />
        {showContractPreview && currentChat?.contractGenerated && (
          <div className="lg:w-1/2 xl:w-2/5 border-l border-slate-200 hidden lg:flex flex-col">
            <ContractPreview chat={currentChat} onClose={() => setShowContractPreview(false)} />
          </div>
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
      <Toaster />
    </AuthProvider>
  );
}
