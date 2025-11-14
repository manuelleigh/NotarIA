import { Download, X, Printer, Share2 } from 'lucide-react';
import { Button } from './ui/button';
import { useEffect, useState } from 'react';
import { getContractDocument } from '../services/apiService';
import { toast } from 'sonner@2.0.3';

export function ContractPreview({ chat, onClose }) {
  const [contractHtml, setContractHtml] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadContract = async () => {
      if (!chat?.apiChatId) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const html = await getContractDocument(chat.apiChatId);
        setContractHtml(html);
      } catch (error) {
        console.error('Error al cargar el contrato:', error);
        toast.error('Error al cargar el documento');
      } finally {
        setIsLoading(false);
      }
    };

    loadContract();
  }, [chat?.apiChatId]);

  const handleDownload = () => {
    if (!contractHtml) return;
    
    const blob = new Blob([contractHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contrato-${chat?.tipoContrato || 'documento'}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success('Documento descargado');
  };

  const handlePrint = () => {
    if (!contractHtml) return;
    
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(contractHtml);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    }
  };

  const handleShare = async () => {
    if (navigator.share && contractHtml) {
      try {
        await navigator.share({
          title: `Contrato ${chat?.tipoContrato || 'Legal'}`,
          text: 'Documento generado por Asistente Notarial IA',
        });
      } catch (error) {
        console.log('Error al compartir:', error);
      }
    } else {
      toast.info('Función de compartir no disponible en este navegador');
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b border-slate-200 p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-slate-900">Vista Previa del Contrato</h3>
            <p className="text-sm text-slate-500 mt-1">
              {chat?.tipoContrato ? `Tipo: ${chat.tipoContrato}` : 'Generado por IA'} • Requiere revisión legal
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="lg:hidden"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 lg:flex-none"
            onClick={handleDownload}
            disabled={!contractHtml || isLoading}
          >
            <Download className="h-4 w-4 mr-2" />
            Descargar
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 lg:flex-none"
            onClick={handlePrint}
            disabled={!contractHtml || isLoading}
          >
            <Printer className="h-4 w-4 mr-2" />
            Imprimir
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 lg:flex-none"
            onClick={handleShare}
            disabled={!contractHtml || isLoading}
          >
            <Share2 className="h-4 w-4 mr-2" />
            Compartir
          </Button>
        </div>
      </div>

      {/* Contract content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 lg:p-8">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-slate-600">Cargando documento...</p>
              </div>
            </div>
          ) : contractHtml ? (
            <>
              {/* Document preview */}
              <div className="bg-white border border-slate-200 shadow-lg rounded-lg p-8 lg:p-12 max-w-4xl mx-auto">
                {/* Renderizar HTML del contrato */}
                <div 
                  className="contract-content text-slate-800"
                  dangerouslySetInnerHTML={{ __html: contractHtml }}
                />
              </div>

              {/* Disclaimer */}
              <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg max-w-4xl mx-auto">
                <p className="text-sm text-amber-800">
                  <strong>Aviso Legal:</strong> Este documento ha sido generado mediante inteligencia artificial 
                  y debe ser revisado por un profesional legal antes de su uso. No constituye asesoría legal.
                </p>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <p className="text-slate-500">No hay documento disponible</p>
                <p className="text-sm text-slate-400 mt-2">
                  Completa la conversación para generar el contrato
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}