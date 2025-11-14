import { useState, useEffect } from 'react';
import { ChatInterface } from './components/ChatInterface';
import { Sidebar } from './components/Sidebar';
import { ContractPreview } from './components/ContractPreview';
import { Auth } from './components/Auth';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { sendChatMessage, getChatHistory, getChatDetail } from './services/apiService';
import { toast } from 'sonner@2.0.3';
import { Toaster } from './components/ui/sonner';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface Chat {
  id: string;
  title: string;
  messages: Message[];
  contractGenerated?: boolean;
  createdAt: Date;
  updatedAt?: Date;
  lastMessage?: string;
  messageCount?: number;
  // Datos de la API
  apiChatId?: number;
  estado?: string;
  tipoContrato?: string;
  respuestas?: Record<string, string>;
  clausulasEspeciales?: string[];
  contratoInfo?: {
    id: number;
    codigo: string;
    titulo: string;
    estado: string;
  };
}

function MainApp() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Auth />;
  }

  return <ChatApp />;
}

function ChatApp() {
  const { apiKey } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [showContractPreview, setShowContractPreview] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const currentChat = chats.find(chat => chat.id === activeChat);

  // Cargar historial al iniciar
  useEffect(() => {
    const loadHistory = async () => {
      if (!apiKey) return;

      try {
        setIsLoadingHistory(true);
        const history = await getChatHistory(apiKey);
        
        console.log('📋 Historial recibido del backend:', history);
        
        const loadedChats: Chat[] = history.map(item => ({
          id: `chat-${item.chat_id}`,
          title: item.nombre,
          messages: [], // Se cargarán cuando se seleccione
          contractGenerated: item.contrato !== null,
          createdAt: new Date(item.fecha_creacion),
          updatedAt: new Date(item.fecha_actualizacion),
          lastMessage: item.ultimo_mensaje,
          messageCount: 0, // Se calculará al cargar el detalle
          apiChatId: item.chat_id,
          estado: item.estado,
          contratoInfo: item.contrato || undefined,
        }));

        console.log('✅ Chats procesados:', loadedChats.map(c => ({
          id: c.id,
          title: c.title,
          contractGenerated: c.contractGenerated,
          contratoInfo: c.contratoInfo
        })));

        setChats(loadedChats);

        // Si no hay chats, no hacer nada (el usuario puede crear uno manualmente)
      } catch (error) {
        console.error('Error al cargar el historial:', error);
        toast.error('Error al cargar las conversaciones');
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [apiKey]);

  // Cargar detalle del chat cuando se selecciona
  const handleSelectChat = async (chatId: string) => {
    setActiveChat(chatId);
    const chat = chats.find(c => c.id === chatId);
    
    // Si el chat ya tiene mensajes cargados, no volver a cargar
    if (chat && chat.messages.length > 0) {
      // Mostrar preview si tiene contrato (no forzar si el usuario lo cerró)
      // El usuario puede usar el botón "Ver Contrato" si lo necesita
      return;
    }

    if (!chat?.apiChatId || !apiKey) return;

    try {
      const detail = await getChatDetail(chat.apiChatId, apiKey);
      
      // Convertir mensajes de la API al formato local
      const messages: Message[] = detail.mensajes.map(msg => ({
        id: `msg-${msg.id}`,
        role: msg.remitente === 'usuario' ? 'user' : 'assistant',
        content: msg.contenido,
        timestamp: new Date(msg.fecha),
      }));

      const hasContract = detail.contrato !== null;

      setChats(prevChats =>
        prevChats.map(c =>
          c.id === chatId
            ? {
                ...c,
                messages,
                messageCount: messages.length,
                tipoContrato: detail.chat.metadatos?.tipo_contrato,
                estado: detail.chat.metadatos?.estado,
                respuestas: detail.chat.metadatos?.respuestas,
                contratoInfo: detail.contrato ? {
                  id: detail.contrato.id,
                  codigo: detail.contrato.codigo,
                  titulo: detail.contrato.titulo,
                  estado: detail.contrato.estado,
                } : undefined,
                contractGenerated: hasContract,
              }
            : c
        )
      );

      // Mostrar preview automáticamente solo la primera vez que se carga
      if (hasContract) {
        setShowContractPreview(true);
      }
    } catch (error) {
      console.error('Error al cargar el detalle del chat:', error);
      toast.error('Error al cargar la conversación');
    }
  };

  const handleNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: 'Nueva Conversación',
      messages: [
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Bienvenido al asistente notarial de IA. ¿Qué tipo de contrato necesita generar hoy?',
          timestamp: new Date()
        }
      ],
      createdAt: new Date()
    };
    setChats([newChat, ...chats]);
    setActiveChat(newChat.id);
    setShowContractPreview(false);
  };

  const handleSendMessage = async (content: string) => {
    if (!currentChat || !apiKey) return;

    const userMessage: Message = {
      id: `${Date.now()}-${Math.random()}`,
      role: 'user',
      content,
      timestamp: new Date()
    };

    // Add user message immediately
    setChats(prevChats =>
      prevChats.map(chat =>
        chat.id === activeChat
          ? { 
              ...chat, 
              messages: [...chat.messages, userMessage],
              lastMessage: content,
              messageCount: (chat.messageCount || chat.messages.length) + 1,
              updatedAt: new Date()
            }
          : chat
      )
    );

    try {
      // Llamar a la API real
      const response = await sendChatMessage(
        content,
        apiKey,
        currentChat.apiChatId
      );

      const aiResponse: Message = {
        id: `${Date.now()}-${Math.random()}`,
        role: 'assistant',
        content: response.respuesta,
        timestamp: new Date()
      };

      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === activeChat
            ? {
                ...chat,
                messages: [...chat.messages, aiResponse],
                title: chat.messages.length === 1 
                  ? (response.tipo_contrato || content.slice(0, 30) + '...') 
                  : chat.title,
                lastMessage: response.respuesta,
                messageCount: (chat.messageCount || chat.messages.length) + 2,
                apiChatId: response.chat_id,
                estado: response.estado,
                tipoContrato: response.tipo_contrato,
                respuestas: response.respuestas,
                clausulasEspeciales: response.clausulas_especiales,
                contractGenerated: response.estado === 'generando_contrato' || 
                                   response.estado === 'esperando_aprobacion_formal' ||
                                   response.estado === 'formalizado',
                updatedAt: new Date()
              }
            : chat
        )
      );

      // Mostrar preview si el contrato está listo
      if (response.estado === 'generando_contrato' || 
          response.estado === 'esperando_aprobacion_formal' ||
          response.estado === 'formalizado') {
        setShowContractPreview(true);
      }
    } catch (error) {
      console.error('Error al enviar mensaje:', error);
      toast.error(error instanceof Error ? error.message : 'Error al enviar mensaje');
      
      // Agregar mensaje de error
      const errorMessage: Message = {
        id: `${Date.now()}-${Math.random()}`,
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo.',
        timestamp: new Date()
      };

      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === activeChat
            ? { 
                ...chat, 
                messages: [...chat.messages, errorMessage],
                lastMessage: errorMessage.content,
                messageCount: (chat.messageCount || chat.messages.length) + 2
              }
            : chat
        )
      );
    }
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar
        chats={chats}
        activeChat={activeChat || ''}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />
      
      <div className="flex flex-1 overflow-hidden">
        <div className={`flex-1 flex flex-col ${showContractPreview ? 'lg:w-1/2' : 'w-full'}`}>
          <ChatInterface
            chat={currentChat}
            onSendMessage={handleSendMessage}
            onTogglePreview={() => setShowContractPreview(!showContractPreview)}
            showPreview={showContractPreview}
          />
        </div>

        {showContractPreview && currentChat?.apiChatId && (
          <div className="hidden lg:block lg:w-1/2 border-l border-slate-200">
            <ContractPreview
              chat={currentChat}
              onClose={() => setShowContractPreview(false)}
            />
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