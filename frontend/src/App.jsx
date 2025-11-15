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

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center h-screen bg-slate-50">
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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const currentChat = chats.find((chat) => chat.id === activeChatId);

  const loadHistory = useCallback(async () => {
    if (!apiKey) return;
    try {
      setIsLoadingHistory(true);
      const history = await getChatHistory(apiKey);
      const loadedChats = history.map((item) => ({
        id: `chat-${item.chat_id}`,
        title: item.nombre,
        messages: [], // Los mensajes se cargarán al seleccionar el chat
        contractGenerated: item.contrato !== null,
        lastMessage: item.ultimo_mensaje,
        apiChatId: item.chat_id,
        contexto: item.metadatos || {},
      }));
      setChats(loadedChats);
    } catch (error) {
      toast.error("Error al cargar historial: " + error.message);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [apiKey]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleSelectChat = async (chatId) => {
    setActiveChatId(chatId);
    const chat = chats.find((c) => c.id === chatId);
    if (!chat?.apiChatId || !apiKey || (chat.messages && chat.messages.length > 0)) {
      setShowContractPreview(chat?.contractGenerated || false);
      return;
    }

    try {
      const detail = await getChatDetail(chat.apiChatId, apiKey);
      const messages = detail.mensajes.map((msg) => ({
        id: `msg-${msg.id}`,
        role: msg.remitente === "usuario" ? "user" : "assistant",
        content: msg.contenido,
        createdAt: new Date(msg.fecha_creacion), // <-- CORREGIDO: Asegurar que createdAt es un objeto Date
      }));

      setChats((prev) =>
        prev.map((c) =>
          c.id === chatId
            ? { ...c, messages, contexto: detail.chat.metadatos, contractGenerated: detail.contrato !== null }
            : c
        )
      );
      setShowContractPreview(detail.contrato !== null);
    } catch (error) {
      toast.error("Error al cargar la conversación: " + error.message);
    }
  };

  const handleNewChat = () => {
    const newChat = {
      id: `new-${Date.now()}`,
      title: "Nuevo Contrato",
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "Bienvenido. ¿Qué contrato necesita?",
          createdAt: new Date(), // <-- CORREGIDO: Añadir fecha de creación
        },
      ],
      contexto: {},
    };
    setChats([newChat, ...chats]);
    setActiveChatId(newChat.id);
    setShowContractPreview(false);
  };

  const handleSendMessage = async (content) => {
    if (!currentChat) return;

    const userMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content,
      createdAt: new Date(), // <-- CORREGIDO: Añadir fecha de creación
    };
    const updatedMessages = [...currentChat.messages, userMessage];
    const assistantMessageId = `${Date.now()}-ai`;

    setChats((prev) =>
      prev.map((chat) => (chat.id === activeChatId ? { ...chat, messages: updatedMessages } : chat))
    );

    try {
      await sendChatMessageStreaming(currentChat.contexto, content, (chunk) => {
        setChats((prev) => {
          return prev.map((chat) => {
            if (chat.id === activeChatId) {
              let newMessages = [...chat.messages];
              let newContext = chat.contexto;

              if (chunk.text) {
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage?.id === assistantMessageId) {
                  newMessages = [
                    ...newMessages.slice(0, -1),
                    { ...lastMessage, content: lastMessage.content + chunk.text },
                  ];
                } else {
                  // <-- CORREGIDO: Añadir fecha de creación al primer chunk del asistente
                  newMessages.push({ id: assistantMessageId, role: "assistant", content: chunk.text, createdAt: new Date() });
                }
              }

              if (chunk.context) {
                newContext = chunk.context;
              }

              return { ...chat, messages: newMessages, contexto: newContext };
            }
            return chat;
          });
        });
      });

    } catch (error) {
      toast.error("Error en la comunicación con el asistente: " + error.message);
    }
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar
        chats={chats}
        activeChat={activeChatId || ""}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        isLoading={isLoadingHistory}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatInterface
          chat={currentChat}
          onSendMessage={handleSendMessage}
          onTogglePreview={() => setShowContractPreview(!showContractPreview)}
          showPreview={showContractPreview && currentChat?.contractGenerated}
        />
        {showContractPreview && currentChat?.contractGenerated && (
          <div className="hidden lg:block lg:w-1/2 border-l">
            <ContractPreview chat={currentChat} onClose={() => setShowContractPreview(false)} />
          </div>
        )}
      </div>
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
