def get_client_ip(request):
    """
    Obtiene la dirección IP real del cliente, considerando si la aplicación
    está detrás de un proxy.
    """
    # El header X-Forwarded-For es el estándar de facto para identificar
    # la IP de origen de un cliente que se conecta a través de un proxy.
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Este header puede contener una lista de IPs: "cliente, proxy1, proxy2"
        # La IP real del cliente es la primera en la lista.
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Si no se está detrás de un proxy, la IP estará en REMOTE_ADDR.
        ip = request.META.get('REMOTE_ADDR')
    return ip