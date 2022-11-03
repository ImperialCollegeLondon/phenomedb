
    # Must be indented!
    @task(multiple_outputs=True)
    def {{task_id}}():
        context = get_current_context()
        try:
            from {{task_module}} import {{task_class}}
            task = {{task_class}}(**{{ task_run.args }},execution_date=context['execution_date'].isoformat(),pipeline_run_id=context['dag_run'].run_id)
            return task.run()
        except Exception as err:
            raise AirflowException(err)

    data_{{task_id}} = {{task_id}}()
    print("data:")
    print(data_{{task_id}})