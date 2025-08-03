from django.shortcuts import render, redirect, get_object_or_404
from .models import Task
from datetime import time, timedelta, datetime
from django.contrib import messages
#from .models import Task, Instructor
from django.http import JsonResponse
from django.db.models import Q

def list_tasks(request):
    tasks = Task.objects.all().order_by('-id')
    #instructores = Instructor.objects.all()
    return render(request, 'list_tasks.html', {
        'tasks': tasks,
      #  'instructores': instructores
    })

def create_task(request):
   # instructores = Instructor.objects.all()

    if request.method == 'POST':
        form_data = request.POST
        instructor_id = form_data.get('instructor')
        fecha_inicio = form_data.get('fecha_inicio')
        fecha_fin = form_data.get('fecha_fin')
        hora = form_data.get('hora')

        # Obtener el nombre del instructor
        instructor_nombre = Instructor.objects.get(id=instructor_id).nombre

        # Buscar tarea en conflicto
        conflict_task = Task.objects.filter(
            instructor=instructor_nombre,  # ✅ ahora compara texto con texto
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio,
            hora=hora
        ).first()

        if conflict_task:
            return render(request, 'create_task.html', {
                'instructores': instructores,
                'form_data': form_data,
                'conflict_task': conflict_task
            })

        # Crear la tarea con el nombre del instructor (no el objeto)
        Task.objects.create(
            instructor=instructor_nombre,  # ✅ se guarda texto
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora=hora,
            title=form_data.get('title'),
            description=form_data.get('description'),
        )
        return redirect('list_tasks')

    return render(request, 'create_task.html', {'instructores': instructores})

def delete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.delete()
    return redirect('list_tasks')

def edit_task(request, id):
    task = get_object_or_404(Task, pk=id)
    instructores = Instructor.objects.all()
    return render(request, 'edit_task.html', {
        'task': task,
        'instructores': instructores
    })

def update_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == 'POST':
        form_data = request.POST
        title = form_data.get('title')
        description = form_data.get('description')
        fecha_inicio = form_data.get('fecha_inicio')
        fecha_fin = form_data.get('fecha_fin')
        hora = form_data.get('hora')
        instructor_id = form_data.get('instructor')

        instructor = Instructor.objects.get(id=instructor_id)
        instructor_nombre = instructor.nombre

        # Buscar conflicto (excluyendo la tarea actual)
        conflict_task = Task.objects.filter(
            instructor=instructor_nombre,
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio,
            hora=hora
        ).exclude(id=task.id).first()

        if conflict_task:
            instructores = Instructor.objects.all()
            return render(request, 'edit_task.html', {
                'task': task,
                'instructores': instructores,
                'conflict_task': conflict_task,
                'form_data': form_data
            })

        # Si no hay conflicto, actualizar
        task.title = title
        task.description = description
        task.fecha_inicio = fecha_inicio
        task.fecha_fin = fecha_fin
        task.hora = hora
        task.instructor = instructor_nombre
        task.save()

        messages.success(request, "Tarea actualizada exitosamente.")
        return redirect('list_tasks')

    instructores = Instructor.objects.all()
    return render(request, 'edit_task.html', {
        'task': task,
        'instructores': instructores
    })

def calendario_clases(request):
    tareas = Task.objects.all().order_by('fecha_inicio', 'hora')
    return render(request, 'calendario.html', {'tareas': tareas})

def api_clases(request):
    tareas = Task.objects.all()
    eventos = []

    for tarea in tareas:
        eventos.append({
            'title': f"{tarea.title} ({tarea.instructor})",
            'start': tarea.fecha_inicio.isoformat() if tarea.fecha_inicio else None,
            'end': tarea.fecha_fin.isoformat() if tarea.fecha_fin else None,
        })

    return JsonResponse(eventos, safe=False)

def reporte_horario_siguiente(request):
    ultima_tarea = Task.objects.order_by('-fecha_fin').first()
    if not ultima_tarea:
        return render(request, 'reporte_horarios.html', {'error': 'No hay tareas registradas.'})

    # 1. Fecha objetivo (día siguiente a la última fecha_fin, sin sábados ni domingos)
    fecha_objetivo = ultima_tarea.fecha_fin + timedelta(days=1)
    while fecha_objetivo.weekday() in [5, 6]:
        fecha_objetivo += timedelta(days=1)

    # 2. Horarios posibles
    hora_inicio = datetime.strptime("07:30", "%H:%M")
    hora_fin = datetime.strptime("17:30", "%H:%M")
    intervalo = timedelta(hours=1, minutes=30)

    horas_posibles = []
    hora_actual = hora_inicio
    while hora_actual <= hora_fin:
        if hora_actual.time() != time(12, 0):
            horas_posibles.append(hora_actual.time())
        hora_actual += intervalo

    # 3. Obtener tareas que estén activas ese día
    tareas_activas = Task.objects.filter(
        Q(fecha_inicio__lte=fecha_objetivo) & Q(fecha_fin__gte=fecha_objetivo)
    )

    # 4. Horas ocupadas en esa fecha
    horas_ocupadas = set()
    for tarea in tareas_activas:
        if tarea.hora:
            horas_ocupadas.add(tarea.hora)

    # 5. Filtrar horas libres
    horas_libres = [h for h in horas_posibles if h not in horas_ocupadas]

    reporte = [{
        'fecha': fecha_objetivo.strftime('%Y-%m-%d'),
        'hora': h.strftime('%H:%M'),
        'estado': 'Libre'
    } for h in horas_libres]

    return render(request, 'reporte_horarios.html', {'reporte': reporte})