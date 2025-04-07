// Variáveis globais para o Bluetooth
var bastaoDevice = null;
var bastaoCharacteristic = null;
var bastaoNotificationsStarted = false;
var bastaoReadInterval = null;
var ultimoBrincoLido = '';
var ultimaLeituraBrinco = 0;
var bastaoErrorCount = 0;
var MAX_CONSECUTIVE_GATT_ERRORS = 5;

// Fila de operações GATT
var gattOperationQueue = [];
var gattOperationInProgress = false;

// UUIDs de serviços Bluetooth conhecidos
const BLUETOOTH_SERVICES = {
    // SPP (Serial Port Profile) - Bluetooth Clássico
    SPP: '00001101-0000-1000-8000-00805f9b34fb',
    // UART - Bluetooth LE
    UART: '6e400001-b5a3-f393-e0a9-e50e24dcca9e',
    // Serviços comuns em leitores de brinco
    FFE0: '0000ffe0-0000-1000-8000-00805f9b34fb',
    FFF0: '0000fff0-0000-1000-8000-00805f9b34fb',
    // HID (Human Interface Device)
    HID: '00001812-0000-1000-8000-00805f9b34fb',
    // Informações do dispositivo
    DEVICE_INFO: '0000180a-0000-1000-8000-00805f9b34fb',
    // Serviços genéricos
    GENERIC_ACCESS: '00001800-0000-1000-8000-00805f9b34fb',
    GENERIC_ATTRIBUTE: '00001801-0000-1000-8000-00805f9b34fb',
    BATTERY: '0000180f-0000-1000-8000-00805f9b34fb'
};

// UUIDs de características Bluetooth conhecidas
const BLUETOOTH_CHARACTERISTICS = {
    // UART
    UART_TX: '6e400002-b5a3-f393-e0a9-e50e24dcca9e', // Para escrita
    UART_RX: '6e400003-b5a3-f393-e0a9-e50e24dcca9e', // Para leitura/notificação
    // Características comuns em leitores de brinco
    FFE1: '0000ffe1-0000-1000-8000-00805f9b34fb',
    FFE2: '0000ffe2-0000-1000-8000-00805f9b34fb',
    FFE3: '0000ffe3-0000-1000-8000-00805f9b34fb',
    FFE4: '0000ffe4-0000-1000-8000-00805f9b34fb',
    FFF1: '0000fff1-0000-1000-8000-00805f9b34fb',
    FFF2: '0000fff2-0000-1000-8000-00805f9b34fb'
};

// Função para executar operações GATT com fila e retry
async function executeGattOperation(operation) {
    return new Promise((resolve, reject) => {
        gattOperationQueue.push({
            operation: operation,
            resolve: resolve,
            reject: reject,
            retryCount: 0,
            maxRetries: 5,  // Aumentado para permitir mais tentativas
            initialBackoff: 800, // Aumentado para dar mais tempo entre tentativas
            currentBackoff: 800
        });
        if (!gattOperationInProgress) {
            processGattQueue();
        }
    });
}

// Função para processar a fila de operações GATT
async function processGattQueue() {
    if (gattOperationQueue.length === 0) {
        gattOperationInProgress = false;
        return;
    }
    
    // Se houver muitos erros consecutivos, pausar a fila
    if (bastaoErrorCount > MAX_CONSECUTIVE_GATT_ERRORS) {
        console.log(`Muitos erros consecutivos (${bastaoErrorCount}), pausando a fila por 3 segundos...`);
        bastaoErrorCount = Math.max(bastaoErrorCount - 1, MAX_CONSECUTIVE_GATT_ERRORS); // Reduzir gradualmente
        setTimeout(() => {
            processGattQueue();
        }, 3000);
        return;
    }
    
    gattOperationInProgress = true;
    const nextOperation = gattOperationQueue.shift();
    
    try {
        const result = await nextOperation.operation();
        nextOperation.resolve(result);
        bastaoErrorCount = 0; // Resetar contador de erros em caso de sucesso
    } catch (error) {
        console.error('Erro na operação GATT:', error);
        
        // Tratamento específico para erro "GATT operation already in progress"
        if (error.message && error.message.includes('GATT operation already in progress')) {
            bastaoErrorCount++;
            // Aguardar um tempo maior para este tipo específico de erro
            const waitTime = 1000 + (bastaoErrorCount * 500); // Aumenta com o número de erros
            console.log(`Erro GATT operation already in progress. Aguardando ${waitTime}ms...`);
            
            // Colocar de volta na fila com um atraso maior
            setTimeout(() => {
                gattOperationQueue.unshift(nextOperation);
                processGattQueue();
            }, waitTime);
            return;
        }
        // Tratamento para erro "GATT operation failed for unknown reason"
        else if (error.message && error.message.includes('GATT operation failed for unknown reason')) {
            bastaoErrorCount++;
            console.log(`Erro GATT operation failed for unknown reason. Tentativa ${bastaoErrorCount}`);
            
            // Tentar uma abordagem alternativa após várias falhas
            if (bastaoErrorCount > 3 && nextOperation.retryCount < nextOperation.maxRetries) {
                console.log('Tentando abordagem alternativa: escrita antes da leitura');
                
                // Colocar de volta na fila com um atraso maior
                setTimeout(() => {
                    gattOperationQueue.unshift(nextOperation);
                    processGattQueue();
                }, 1500);
                return;
            }
        }
        // Tratamento para outros erros
        else {
            bastaoErrorCount++;
            
            // Verificar se deve tentar novamente
            if (nextOperation.retryCount < nextOperation.maxRetries) {
                console.log(`Tentando novamente (${nextOperation.retryCount + 1}/${nextOperation.maxRetries}) após ${nextOperation.currentBackoff}ms...`);
                
                // Incrementar contador de tentativas e backoff
                nextOperation.retryCount++;
                nextOperation.currentBackoff = Math.min(nextOperation.currentBackoff * 2, 5000); // Backoff exponencial, máximo 5 segundos
                
                // Colocar de volta na fila
                setTimeout(() => {
                    gattOperationQueue.unshift(nextOperation);
                    processGattQueue();
                }, nextOperation.currentBackoff);
                return;
            } else {
                console.error('Número máximo de tentativas excedido');
                nextOperation.reject(error);
            }
        }
    } finally {
        // Processar próxima operação após um intervalo maior
        setTimeout(() => {
            processGattQueue();
        }, 500); // Aumentado para dar mais tempo entre operações
    }
}

// Função para conectar ao bastão Bluetooth
async function conectarBastao() {
    try {
        // Resetar contadores de erro no início da conexão
        bastaoErrorCount = 0;
        const bastaoStatusDiv = document.getElementById('bastaoStatus');
        bastaoStatusDiv.textContent = "Conectando...";
        
        // Verificar se já está conectado
        if (bastaoDevice && bastaoDevice.gatt.connected) {
            console.log('Bastão já está conectado');
            bastaoStatusDiv.textContent = "Conectado a " + bastaoDevice.name;
            return;
        }
        
        // Solicitar dispositivo Bluetooth
        // Solicitar dispositivo Bluetooth
        bastaoDevice = await navigator.bluetooth.requestDevice({
            // Aceitar qualquer dispositivo Bluetooth para garantir a descoberta
            acceptAllDevices: true,
            // Incluir todos os serviços conhecidos
            optionalServices: [
                BLUETOOTH_SERVICES.SPP,       // SPP (Serial Port Profile)
                BLUETOOTH_SERVICES.UART,      // UART
                BLUETOOTH_SERVICES.FFE0,      // FFE0 - Comum em leitores
                BLUETOOTH_SERVICES.FFF0,      // FFF0 - Comum em leitores
                BLUETOOTH_SERVICES.HID,       // HID
                BLUETOOTH_SERVICES.DEVICE_INFO, // Device Information
                'device_information',         // Alternativa para Device Information
                BLUETOOTH_SERVICES.GENERIC_ACCESS,    // Generic Access
                BLUETOOTH_SERVICES.GENERIC_ATTRIBUTE, // Generic Attribute
                BLUETOOTH_SERVICES.BATTERY    // Battery Service
            ]
        });
        
        console.log('Dispositivo selecionado:', bastaoDevice.name, 'ID:', bastaoDevice.id);
        bastaoDevice.addEventListener('gattserverdisconnected', onBastaoDisconnected);
        
        // Conectar ao GATT server
        console.log('Conectando ao GATT server do bastão...');
        const server = await executeGattOperation(() => bastaoDevice.gatt.connect());
        
        // Descobrir serviços - Priorizar serviços conhecidos na ordem
        console.log('Descobrindo serviços...');
        const services = await executeGattOperation(() => server.getPrimaryServices());
        console.log('Serviços descobertos:', services.map(s => s.uuid));
        
        // Ordenar serviços por prioridade (SPP > UART > FFE0 > FFF0 > outros)
        const priorityOrder = {
            [BLUETOOTH_SERVICES.SPP]: 1,   // Maior prioridade para SPP
            [BLUETOOTH_SERVICES.UART]: 2,  // Depois UART
            [BLUETOOTH_SERVICES.FFE0]: 3,  // Depois FFE0
            [BLUETOOTH_SERVICES.FFF0]: 4   // Depois FFF0
        };
        
        // Ordenar serviços por prioridade
        const sortedServices = [...services].sort((a, b) => {
            const priorityA = priorityOrder[a.uuid] || 999;
            const priorityB = priorityOrder[b.uuid] || 999;
            return priorityA - priorityB;
        });
        
        console.log('Serviços ordenados por prioridade:', sortedServices.map(s => s.uuid));
        
        // Procurar por características em cada serviço
        let foundCharacteristic = false;
        
        for (const service of sortedServices) {
            try {
                console.log('Descobrindo características para serviço:', service.uuid);
                const characteristics = await executeGattOperation(() => service.getCharacteristics());
                console.log('Características descobertas:', characteristics.map(c => c.uuid));
                
                // Procurar por características conhecidas em ordem de prioridade
                const targetCharUUIDs = [
                    BLUETOOTH_CHARACTERISTICS.UART_RX,  // UART RX
                    BLUETOOTH_CHARACTERISTICS.FFE1,    // FFE1
                    BLUETOOTH_CHARACTERISTICS.FFE2,    // FFE2
                    BLUETOOTH_CHARACTERISTICS.FFE3,    // FFE3
                    BLUETOOTH_CHARACTERISTICS.FFE4,    // FFE4
                    BLUETOOTH_CHARACTERISTICS.FFF1,    // FFF1
                    BLUETOOTH_CHARACTERISTICS.FFF2     // FFF2
                ];
                
                for (const uuid of targetCharUUIDs) {
                    const char = characteristics.find(c => c.uuid === uuid);
                    if (char) {
                        bastaoCharacteristic = char;
                        console.log('Encontrada característica alvo:', uuid);
                        foundCharacteristic = true;
                        break;
                    }
                }
                
                if (foundCharacteristic) break;
                
                // Se não encontrou características conhecidas, procurar por qualquer uma que suporte notificações
                if (!bastaoCharacteristic) {
                    const notifyChar = characteristics.find(c => c.properties && (c.properties.notify || c.properties.indicate));
                    if (notifyChar) {
                        bastaoCharacteristic = notifyChar;
                        console.log('Usando característica com notificação:', notifyChar.uuid);
                        foundCharacteristic = true;
                        break;
                    }
                }
                
                // Se ainda não encontrou, procurar por qualquer uma que suporte leitura
                if (!bastaoCharacteristic) {
                    const readChar = characteristics.find(c => c.properties && c.properties.read);
                    if (readChar) {
                        bastaoCharacteristic = readChar;
                        console.log('Usando característica com leitura:', readChar.uuid);
                        foundCharacteristic = true;
                        break;
                    }
                }
                
                // Última opção: qualquer característica disponível
                if (!bastaoCharacteristic && characteristics.length > 0) {
                    bastaoCharacteristic = characteristics[0];
                    console.log('Usando primeira característica disponível:', bastaoCharacteristic.uuid);
                    foundCharacteristic = true;
                    break;
                }
            } catch (error) {
                console.warn('Erro ao descobrir características para serviço', service.uuid, error);
            }
        }
        
        if (!bastaoCharacteristic) {
            throw new Error('Não foi possível encontrar uma característica compatível no bastão');
        }
        
        console.log('Propriedades da característica:', {
            notify: bastaoCharacteristic.properties && bastaoCharacteristic.properties.notify,
            indicate: bastaoCharacteristic.properties && bastaoCharacteristic.properties.indicate,
            read: bastaoCharacteristic.properties && bastaoCharacteristic.properties.read,
            write: bastaoCharacteristic.properties && bastaoCharacteristic.properties.write,
            writeWithoutResponse: bastaoCharacteristic.properties && bastaoCharacteristic.properties.writeWithoutResponse
        });
        
        // Iniciar notificações ou leitura periódica com sistema de fallback
        if (bastaoCharacteristic.properties && (bastaoCharacteristic.properties.notify || bastaoCharacteristic.properties.indicate)) {
            console.log('Iniciando notificações para o bastão...');
            try {
                await executeGattOperation(() => bastaoCharacteristic.startNotifications());
                bastaoCharacteristic.addEventListener('characteristicvaluechanged', handleBastaoValueChanged);
                bastaoNotificationsStarted = true;
                console.log('Notificações iniciadas com sucesso');
                
                // Tentar ler o valor inicial mesmo com notificações ativas
                setTimeout(async () => {
                    try {
                        await executeGattOperation(() => bastaoCharacteristic.readValue());
                        console.log('Leitura inicial bem-sucedida com notificações ativas');
                    } catch (error) {
                        console.log('Erro na leitura inicial com notificações ativas (ignorando):', error);
                    }
                }, 500);
            } catch (error) {
                console.warn('Falha ao iniciar notificações, usando fallback para leitura periódica:', error);
                configurarLeituraPeriodica();
            }
        } else if (bastaoCharacteristic.properties && bastaoCharacteristic.properties.read) {
            console.log('Característica não suporta notificações, usando leitura periódica');
            configurarLeituraPeriodica();
        } else {
            console.warn('Característica não suporta notificações nem leitura direta, tentando abordagem alternativa');
            // Tentar escrever antes de ler como última opção
            if (bastaoCharacteristic.properties && (bastaoCharacteristic.properties.write || bastaoCharacteristic.properties.writeWithoutResponse)) {
                console.log('Tentando usar escrita para ativar o dispositivo');
                try {
                    // Enviar comando de ativação (0x01 é comum para ativar leitores)
                    const activationCommand = new Uint8Array([0x01]);
                    await executeGattOperation(() => bastaoCharacteristic.writeValue(activationCommand));
                    console.log('Comando de ativação enviado, configurando leitura periódica');
                    configurarLeituraPeriodica();
                } catch (error) {
                    console.error('Falha na abordagem alternativa:', error);
                    throw new Error('A característica não suporta operações compatíveis');
                }
            } else {
                throw new Error('A característica não suporta notificações, leitura ou escrita');
            }
        }
        
        // Função interna para configurar leitura periódica
        function configurarLeituraPeriodica() {
            // Limpar intervalo anterior se existir
            if (bastaoReadInterval) {
                clearInterval(bastaoReadInterval);
                bastaoReadInterval = null;
            }
            
            // Adiciona um atraso antes da primeira leitura
            setTimeout(async () => {
                // Tenta ler o valor inicial com múltiplas tentativas
                let initialReadSuccess = false;
                const initialDelays = [1000, 1200, 1500]; // Tentar com diferentes delays
                
                for (const delay of initialDelays) {
                    if (initialReadSuccess) break;
                    
                    try {
                        console.log(`Tentando leitura inicial com delay de ${delay}ms...`);
                        await new Promise(resolve => setTimeout(resolve, delay));
                        await executeGattOperation(() => bastaoCharacteristic.readValue());
                        const initialValue = bastaoCharacteristic.value;
                        handleBastaoValueChanged({ target: { value: initialValue } });
                        bastaoErrorCount = 0; // Resetar contador de erros
                        initialReadSuccess = true;
                        console.log('Leitura inicial bem-sucedida');
                    } catch (error) {
                        console.error(`Erro na leitura inicial com delay ${delay}ms:`, error);
                        bastaoErrorCount++;
                    }
                }

                // Configura leitura periódica
                console.log('Configurando leitura periódica para o bastão...');
                bastaoReadInterval = setInterval(async () => {
                    if (!bastaoCharacteristic || !bastaoDevice || !bastaoDevice.gatt.connected) {
                        console.log('Dispositivo ou característica não disponível, interrompendo leitura');
                        clearInterval(bastaoReadInterval);
                        bastaoReadInterval = null;
                        return;
                    }
                    
                    try {
                        // Tentar escrita antes da leitura se houver muitos erros
                        if (bastaoErrorCount > 3 && bastaoCharacteristic.properties && 
                            (bastaoCharacteristic.properties.write || bastaoCharacteristic.properties.writeWithoutResponse)) {
                            console.log('Tentando escrita antes da leitura devido a erros anteriores');
                            try {
                                const activationCommand = new Uint8Array([0x01]);
                                await executeGattOperation(() => bastaoCharacteristic.writeValue(activationCommand));
                            } catch (writeError) {
                                console.log('Erro na escrita prévia (ignorando):', writeError);
                            }
                        }
                        
                        await executeGattOperation(() => bastaoCharacteristic.readValue());
                        const value = bastaoCharacteristic.value;
                        handleBastaoValueChanged({ target: { value } });
                        bastaoErrorCount = 0; // Resetar contador de erros após leitura bem-sucedida
                    } catch (error) {
                        console.error('Erro na leitura periódica do bastão:', error);
                        bastaoErrorCount++;
                        
                        // Tratamento específico para erros comuns
                        if (error.name === 'NotSupportedError' || 
                            (error.message && error.message.includes('GATT operation failed for unknown reason'))) {
                            console.log('Erro GATT detectado, aguardando antes da próxima tentativa...');
                            // Não interromper a leitura, apenas aguardar mais tempo
                            await new Promise(resolve => setTimeout(resolve, 1000 + (bastaoErrorCount * 200)));
                        } else if (bastaoErrorCount > MAX_CONSECUTIVE_GATT_ERRORS) {
                            console.log('Muitos erros consecutivos, interrompendo leitura periódica');
                            clearInterval(bastaoReadInterval);
                            bastaoReadInterval = null;
                            
                            // Tentar reconectar após um tempo
                            setTimeout(() => {
                                if (!bastaoDevice || !bastaoDevice.gatt.connected) {
                                    console.log('Tentando reconectar ao bastão...');
                                    conectarBastao().catch(e => console.error('Falha ao reconectar:', e));
                                } else {
                                    // Reiniciar leitura periódica
                                    configurarLeituraPeriodica();
                                }
                            }, 5000); // Aguardar 5 segundos antes de tentar reconectar
                        }
                    }
                }, 1000); // Intervalo de 1 segundo para evitar sobrecarga
            }, 500); // Atraso de 500ms antes da primeira leitura
        }
        
        bastaoStatusDiv.textContent = "Conectado a " + bastaoDevice.name;
        mostrarNotificacao("Bastão conectado com sucesso!", "success");
        
    } catch (error) {
        console.error('Erro ao conectar ao bastão:', error);
        const bastaoStatusDiv = document.getElementById('bastaoStatus');
        bastaoStatusDiv.textContent = "Erro: " + error.message;
        mostrarNotificacao("Erro ao conectar ao bastão: " + error.message, "error");
        throw error;
    }
}

// Variáveis para controle de leituras de brinco
let ultimoTempoLeitura = 0;
const INTERVALO_MINIMO_LEITURA = 500; // 500ms entre leituras do mesmo brinco

// Função para processar as leituras do bastão
function handleBastaoValueChanged(event) {
    try {
        const value = event.target.value;
        if (!value) {
            console.log('Valor recebido vazio, ignorando');
            return;
        }
        
        // Obter os bytes brutos para debug
        const bytes = new Uint8Array(value.buffer);
        const hexString = Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join(' ');
        console.log('Dados brutos recebidos (hex):', hexString);
        
        // Tentar diferentes métodos de decodificação
        let brincoLido = "";
        let metodoUsado = "";
        
        // Método 1: Decodificar como texto
        try {
            const textoDecodificado = new TextDecoder().decode(value).trim();
            if (textoDecodificado && !/^[\x00\s]*$/.test(textoDecodificado)) {
                brincoLido = textoDecodificado;
                metodoUsado = "UTF-8";
                console.log('Decodificado como texto:', brincoLido);
            }
        } catch (decodeError) {
            console.warn('Erro ao decodificar como texto:', decodeError);
        }
        
        // Método 2: Se o método 1 falhar ou retornar string vazia/inválida
        if (!brincoLido) {
            // Tentar extrair caracteres ASCII imprimíveis
            const asciiChars = Array.from(bytes)
                .filter(b => b >= 32 && b <= 126) // Apenas caracteres ASCII imprimíveis
                .map(b => String.fromCharCode(b))
                .join('');
                
            if (asciiChars && asciiChars.trim()) {
                brincoLido = asciiChars.trim();
                metodoUsado = "ASCII";
                console.log('Extraído como ASCII:', brincoLido);
            } else {
                // Tentar interpretar como número (big-endian e little-endian)
                if (bytes.length >= 4) {
                    const view = new DataView(value.buffer);
                    const numBE = view.getUint32(0, false); // Big Endian
                    const numLE = view.getUint32(0, true);  // Little Endian
                    
                    console.log('Possíveis interpretações numéricas:', {
                        bigEndian: numBE,
                        littleEndian: numLE
                    });
                    
                    // Usar o número se for razoável (não zero e não muito grande)
                    if (numBE > 0 && numBE < 1000000000) {
                        brincoLido = numBE.toString();
                        metodoUsado = "Numérico (BE)";
                        console.log('Usando interpretação numérica (BE):', brincoLido);
                    } else if (numLE > 0 && numLE < 1000000000) {
                        brincoLido = numLE.toString();
                        metodoUsado = "Numérico (LE)";
                        console.log('Usando interpretação numérica (LE):', brincoLido);
                    }
                }
            }
        }
        
        // Verificar se o brinco é válido (não vazio e não contém apenas caracteres nulos)
        const brincoValido = brincoLido && 
                            !/^[\x00\s]*$/.test(brincoLido) && // Não contém apenas nulos ou espaços
                            brincoLido.length > 1 && // Tem pelo menos 2 caracteres
                            brincoLido.length < 30; // Não é muito longo (provavelmente erro)
        
        // Verificar se já passou tempo suficiente desde a última leitura (500ms)
        const agora = Date.now();
        const tempoDesdeUltimaLeitura = agora - ultimoTempoLeitura;
        
        // Verificar se é diferente do último brinco lido
        const mesmoQueAnterior = brincoLido === ultimoBrincoLido;
        
        // Critério para processamento: brinco válido e (novo ou passou tempo suficiente)
        const deveProcessar = brincoValido && 
                             (!mesmoQueAnterior || tempoDesdeUltimaLeitura > INTERVALO_MINIMO_LEITURA);
        
        console.log('Análise de leitura:', {
            brinco: brincoLido,
            metodoUsado,
            valido: brincoValido,
            mesmoQueAnterior,
            tempoDesdeUltimaLeitura,
            deveProcessar
        });
        
        // Processar o brinco se for válido e não for uma leitura duplicada recente
        if (deveProcessar) {
            console.log('Brinco válido lido:', brincoLido, 'Método:', metodoUsado);
            
            // Atualizar o campo de brinco
            const brincoField = document.getElementById('id_brinco');
            if (brincoField) {
                brincoField.value = brincoLido;
                brincoField.dispatchEvent(new Event('change'));
                
                // Notificar o usuário
                mostrarNotificacao("Brinco lido: " + brincoLido, "success");
                
                // Atualizar controle de duplicatas
                ultimoBrincoLido = brincoLido;
                ultimoTempoLeitura = agora;
                
                // Resetar contador de erros após leitura bem-sucedida
                bastaoErrorCount = 0;
            }
        } else if (brincoValido && mesmoQueAnterior) {
            console.log('Ignorando leitura duplicada recente:', brincoLido);
        } else if (!brincoValido) {
            console.log('Ignorando leitura inválida:', brincoLido);
        }
    } catch (error) {
        console.error('Erro ao processar dados do bastão:', error);
    }
}

// Função para tratar desconexão do bastão
function onBastaoDisconnected() {
    bastaoNotificationsStarted = false;
    bastaoCharacteristic = null;
    
    // Limpar intervalo de leitura se existir
    if (bastaoReadInterval) {
        clearInterval(bastaoReadInterval);
        bastaoReadInterval = null;
    }
    
    const bastaoStatusDiv = document.getElementById('bastaoStatus');
    bastaoStatusDiv.textContent = "Desconectado";
    const bastaoBtn = document.getElementById('conectarBastao');
    if (bastaoBtn) {
        bastaoBtn.textContent = "Reconectar";
    }
}
