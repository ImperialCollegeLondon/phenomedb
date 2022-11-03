    # Must be indented!
    @task(multiple_outputs=True)
    def {{ task_id }}():
        context = get_current_context()
        try:
            from {{task_module}} import {{task_class}}
            if context['dag_run'].conf == {}:
                task = {{task_class}}(execution_date=context['execution_date'].isoformat(),pipeline_run_id=context['dag_run'].run_id)
                return task.run()
            elif '{{ task_id }}' in context['dag_run'].conf:
                args = context['dag_run'].conf.get('{{ task_id }}')
                args['execution_date'] = context['execution_date'].isoformat()
                args['pipeline_run_id'] = context['dag_run'].run_id
                task = {{task_class}}(**args)
                return task.run()
            else:
                return {}
        except Exception as err:
            raise AirflowException(err)

    data_{{ task_id }} = {{ task_id }}()
    print("data:")
    print(data_{{ task_id }})