// Função para mostrar notificações SweetAlert2
function showNotification(type, message) {
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer)
            toast.addEventListener('mouseleave', Swal.resumeTimer)
        }
    });

    // Mapeia os tipos de mensagem do Django para os ícones do SweetAlert2
    const iconMap = {
        'success': 'success',
        'error': 'error',
        'warning': 'warning',
        'info': 'info',
        'debug': 'info'
    };

    Toast.fire({
        icon: iconMap[type] || 'info',
        title: message
    });
}

// Função para confirmação de exclusão
function confirmDelete(url, itemName) {
    Swal.fire({
        title: 'Confirmar exclusão',
        text: `Deseja realmente excluir ${itemName}?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sim, excluir!',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
    return false;
}
