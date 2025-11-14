const API_BASE_URL = 'http://127.0.0.1:5000';

export interface ChatResponse {
  chat_id: number;
  respuesta: string;
  estado: string;
  tipo_contrato?: string;
  pregunta_actual: number;
  respuestas: Record<string, string>;
  clausulas_especiales: string[];
}

export interface ChatHistoryItem {
  chat_id: number;
  nombre: string;
  estado: string;
  fecha_creacion: string;
  fecha_actualizacion: string;
  ultimo_mensaje: string;
  contrato: {
    id: number;
    codigo: string;
    titulo: string;
    estado: string;
  } | null;
}

export interface ChatDetailMessage {
  id: number;
  remitente: 'usuario' | 'asistente';
  contenido: string;
  fecha: string;
  contrato_id: number | null;
}

export interface ChatDetail {
  chat: {
    id: number;
    nombre: string;
    estado: string;
    metadatos: {
      estado: string;
      pregunta_actual: string;
      tipo_contrato: string;
      respuestas: Record<string, any>;
    };
    fecha_creacion: string;
    fecha_actualizacion: string;
  };
  mensajes: ChatDetailMessage[];
  contrato: {
    id: number;
    codigo: string;
    titulo: string;
    estado: string;
    contenido: Record<string, any>;
    archivo_original_url: string | null;
  } | null;
}

export async function getChatHistory(apiKey: string): Promise<ChatHistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}/chat/historial`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Token requerido');
    }
    throw new Error('Error al obtener el historial');
  }

  return response.json();
}

export async function getChatDetail(chatId: number, apiKey: string): Promise<ChatDetail> {
  const response = await fetch(`${API_BASE_URL}/chat/${chatId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Token requerido');
    }
    if (response.status === 404) {
      throw new Error('Chat no encontrado');
    }
    throw new Error('Error al obtener el chat');
  }

  return response.json();
}

export async function sendChatMessage(
  mensaje: string,
  apiKey: string,
  chatId?: number
): Promise<ChatResponse> {
  const body: { mensaje: string; chat_id?: number } = { mensaje };
  if (chatId) {
    body.chat_id = chatId;
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Token requerido');
    }
    if (response.status === 403) {
      throw new Error('Usuario no autorizado');
    }
    if (response.status === 404) {
      throw new Error('Chat no encontrado');
    }
    throw new Error('Error al enviar mensaje');
  }

  return response.json();
}

export async function getContractDocument(chatId: number): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/chat/documento?chat_id=${chatId}`, {
    method: 'GET',
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Chat no encontrado');
    }
    throw new Error('Error al obtener el documento');
  }

  return response.text();
}