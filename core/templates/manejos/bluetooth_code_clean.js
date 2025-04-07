// Variáveis globais para o Bluetooth
var bastaoDevice = null;
var bastaoCharacteristic = null;
var bastaoNotificationsStarted = false;
var bastaoReadInterval = null;
var ultimoBrincoLido = '';
var ultimaLeituraBrinco = 0;
var errorCount = 0;
var MAX_CONSECUTIVE_GATT_ERRORS = 5;

// Fila de operações GATT
var gattOperationQueue = [];
var gattOperationInProgress = false;

// Função para executar operações GATT com fila e retry
async function executeGattOperation(operation) {
    return new Promise((resolve, reject) => {
        gattOperationQueue.push({
            operation: operation,
            resolve: resolve,
            reject: reject,
            retryCount: 0,
            maxRetries: 5,
            initialBackoff: 100,
            currentBackoff: 100
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
    
    gattOperationInProgress = true;
    const nextOperation = gattOperationQueue.shift();
    
    try {
        const result = await nextOperation.operation();
        nextOperation.resolve(result);
        errorCount = 0; // Resetar contador de erros em caso de sucesso
    } catch (error) {
        console.error('Erro na operação GATT:', error);
        errorCount++;
        
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
    } finally {
        // Processar próxima operação após um pequeno intervalo
        setTimeout(() => {
            processGattQueue();
        }, 200);
    }
}

// Função para conectar ao bastão Bluetooth
async function conectarBastao() {
    try {
        const bastaoStatusDiv = document.getElementById('bastaoStatus');
        bastaoStatusDiv.textContent = "Conectando...";
        
        // Verificar se já está conectado
        if (bastaoDevice && bastaoDevice.gatt.connected) {
            console.log('Bastão já está conectado');
            bastaoStatusDiv.textContent = "Conectado a " + bastaoDevice.name;
            return;
        }
        
        // Solicitar dispositivo Bluetooth
        bastaoDevice = await navigator.bluetooth.requestDevice({
            filters: [
                { services: ['00001101-0000-1000-8000-00805f9b34fb'] }, // SPP
                { services: ['6e400001-b5a3-f393-e0a9-e50e24dcca9e'] }, // UART
                { services: ['0000ffe0-0000-1000-8000-00805f9b34fb'] }, // FFE0
                { services: ['0000fff0-0000-1000-8000-00805f9b34fb'] }, // FFF0
                { services: ['00001812-0000-1000-8000-00805f9b34fb'] }, // HID
                { namePrefix: 'RFID' },
                { namePrefix: 'LEITOR' },
                { namePrefix: 'READER' },
                { namePrefix: 'HC-' },
                { namePrefix: 'BT' }
            ],
            optionalServices: [
                '00001101-0000-1000-8000-00805f9b34fb', // SPP
                '6e400001-b5a3-f393-e0a9-e50e24dcca9e', // UART
                '0000ffe0-0000-1000-8000-00805f9b34fb', // FFE0
                '0000fff0-0000-1000-8000-00805f9b34fb', // FFF0
                '00001812-0000-1000-8000-00805f9b34fb', // HID
                '0000180a-0000-1000-8000-00805f9b34fb', // Device Info
                '00001800-0000-1000-8000-00805f9b34fb'  // Generic Access
            ]
        });
        
        // Adicionar listener para desconexão
        bastaoDevice.addEventListener('gattserverdisconnected', onBastaoDisconnected);
        
        // Conectar ao GATT server
        console.log('Conectando ao GATT server do bastão...');
        const server = await executeGattOperation(() => bastaoDevice.gatt.connect());
        
        // Descobrir serviços
        console.log('Descobrindo serviços...');
        const services = await executeGattOperation(() => server.getPrimaryServices());
        console.log('Serviços descobertos:', services.map(s => s.uuid));
        
        // Procurar por características em cada serviço
        let foundCharacteristic = false;
        
        for (const service of services) {
            try {
                console.log('Descobrindo características para serviço:', service.uuid);
                const characteristics = await executeGattOperation(() => service.getCharacteristics());
                console.log('Características descobertas:', characteristics.map(c => c.uuid));
                
                // Procurar por características conhecidas
                const targetCharUUIDs = [
                    '6e400003-b5a3-f393-e0a9-e50e24dcca9e', // UART RX
                    '0000ffe1-0000-1000-8000-00805f9b34fb', // FFE1
                    '0000fff1-0000-1000-8000-00805f9b34fb'  // FFF1
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
                    const notifyChar = characteristics.find(c => c.properties.notify || c.properties.indicate);
                    if (notifyChar) {
                        bastaoCharacteristic = notifyChar;
                        console.log('Usando característica com notificação:', notifyChar.uuid);
                        foundCharacteristic = true;
                        break;
                    }
                }
                
                // Se ainda não encontrou, procurar por qualquer uma que suporte leitura
                if (!bastaoCharacteristic) {
                    const readChar = characteristics.find(c => c.properties.read);
                    if (readChar) {
                        bastaoCharacteristic = readChar;
                        console.log('Usando característica com leitura:', readChar.uuid);
                        foundCharacteristic = true;
                        break;
                    }
                }
            } catch (error) {
                console.warn('Erro ao descobrir características para serviço', service.uuid, error);
            }
        }
        
        if (!bastaoCharacteristic) {
            throw new Error('Não foi possível encontrar uma característica compatível no bastão');
        }
        
        // Iniciar notificações ou leitura periódica
        if (bastaoCharacteristic.properties.notify || bastaoCharacteristic.properties.indicate) {
            console.log('Iniciando notificações para o bastão...');
            await executeGattOperation(() => bastaoCharacteristic.startNotifications());
            bastaoCharacteristic.addEventListener('characteristicvaluechanged', handleBastaoValueChanged);
            bastaoNotificationsStarted = true;
        } else if (bastaoCharacteristic.properties.read) {
            console.log('Configurando leitura periódica para o bastão...');
            // Ler imediatamente
            setTimeout(async () => {
                try {
                    const value = await executeGattOperation(() => bastaoCharacteristic.readValue());
                    handleBastaoValueChanged({ target: { value } });
                } catch (error) {
                    console.error('Erro na leitura inicial do bastão:', error);
                }
            }, 500);
            
            // Configurar leitura periódica
            bastaoReadInterval = setInterval(async () => {
                try {
                    const value = await executeGattOperation(() => bastaoCharacteristic.readValue());
                    handleBastaoValueChanged({ target: { value } });
                } catch (error) {
                    console.error('Erro na leitura periódica do bastão:', error);
                    errorCount++;
                    
                    if (errorCount > MAX_CONSECUTIVE_GATT_ERRORS) {
                        clearInterval(bastaoReadInterval);
                        bastaoReadInterval = null;
                        console.error('Muitos erros consecutivos, interrompendo leitura periódica');
                    }
                }
            }, 1000); // Intervalo de 1 segundo para o bastão
        } else {
            throw new Error('A característica não suporta notificações nem leitura');
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

// Função para processar as leituras do bastão
function handleBastaoValueChanged(event) {
    try {
        const value = event.target.value;
        const brincoInput = document.getElementById('brinco');
        
        // Exibir dados brutos para depuração
        console.log('Dados brutos recebidos do bastão:', Array.from(new Uint8Array(value.buffer)).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        // Tentar diferentes decodificações
        const decoder = new TextDecoder('utf-8');
        let brincoLido = decoder.decode(value).trim();
        
        // Se o brinco estiver vazio ou contiver apenas caracteres nulos, tente outras abordagens
        if (!brincoLido || /^[\x00\s]*$/.test(brincoLido)) {
            // Tentar extrair caracteres ASCII válidos
            const bytes = new Uint8Array(value.buffer);
            const asciiChars = [];
            
            for (let i = 0; i < bytes.length; i++) {
                // Considerar apenas caracteres ASCII imprimíveis (32-126)
                if (bytes[i] >= 32 && bytes[i] <= 126) {
                    asciiChars.push(String.fromCharCode(bytes[i]));
                }
            }
            
            if (asciiChars.length > 0) {
                brincoLido = asciiChars.join('');
                console.log('Brinco extraído de caracteres ASCII:', brincoLido);
            }
            
            // Se ainda estiver vazio, tente interpretar como número
            if (!brincoLido || /^[\x00\s]*$/.test(brincoLido)) {
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
                        console.log('Usando interpretação numérica (BE):', brincoLido);
                    } else if (numLE > 0 && numLE < 1000000000) {
                        brincoLido = numLE.toString();
                        console.log('Usando interpretação numérica (LE):', brincoLido);
                    }
                }
            }
        }
        
        console.log('Brinco lido após processamento:', brincoLido);
        
        // Verificar se o brinco é válido (não vazio e não contém apenas caracteres nulos)
        const brincoValido = brincoLido && 
                            !/^[\x00\s]*$/.test(brincoLido) && // Não contém apenas nulos ou espaços
                            brincoLido.length > 1 && // Tem pelo menos 2 caracteres
                            brincoLido.length < 30; // Não é muito longo (provavelmente erro)
        
        // Verificar se já passou tempo suficiente desde a última leitura (500ms)
        const agora = Date.now();
        const tempoSuficiente = (agora - ultimaLeituraBrinco) > 500;
        
        // Verificar se é diferente do último brinco lido
        const brincoNovo = brincoLido !== ultimoBrincoLido;
        
        console.log('Dados recebidos do bastão:', {
            bruto: brincoLido,
            valido: brincoValido,
            novo: brincoNovo,
            tempoSuficiente: tempoSuficiente
        });
        
        // Só processa se for um brinco válido, novo e tiver passado tempo suficiente
        if (brincoValido && (brincoNovo || tempoSuficiente)) {
            console.log('Brinco válido lido:', brincoLido);
            
            // Atualizar variáveis de controle
            ultimoBrincoLido = brincoLido;
            ultimaLeituraBrinco = agora;
            
            // Preencher o campo de brinco
            brincoInput.value = brincoLido;
            
            // Disparar evento de busca de animal
            buscarAnimal(brincoLido);
            
            // Reproduzir beep de confirmação
            beep();
            
            // Focar no próximo campo se automação estiver ativa
            if (automationActive) {
                pesoInput.focus();
            }
            
            // Mostrar notificação
            mostrarNotificacao("Brinco lido: " + brincoLido, "success");
        }
    } catch (error) {
        console.error('Erro ao processar leitura do bastão:', error);
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
