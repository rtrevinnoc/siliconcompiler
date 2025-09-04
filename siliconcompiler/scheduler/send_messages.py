"""
A module for sending email notifications about SiliconCompiler job events.

This module provides functionality to send detailed email updates at various
stages of a compilation flow (e.g., on begin, failure, or a final summary).
It loads SMTP server credentials from a configuration file, constructs
HTML-formatted emails with relevant job data and attachments (logs, images),
and sends them to specified recipients.
"""
import fastjsonschema
import json
import os
import smtplib
import uuid

import os.path
from email.mime.multipart import MIMEMultipart

from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

from siliconcompiler import sc_open
from siliconcompiler.utils import default_email_credentials_file, get_file_template
from siliconcompiler.report import utils as report_utils
from siliconcompiler.schema import Parameter
from siliconcompiler.flowgraph import RuntimeFlowgraph


# Compile validation code for API request bodies.
api_dir = Path(__file__).parent / 'validation'

# 'remote_run': Run a stage of a job using the server's cluster settings.
with open(api_dir / 'email_credentials.json') as schema:
    validate_creds = fastjsonschema.compile(json.loads(schema.read()))


def __load_config(chip):
    """
    Loads and validates email credentials from the default configuration file.

    This function locates the email credentials JSON file, loads its content,
    and validates it against a predefined JSON schema.

    Args:
        chip (Chip): The Chip object, used for logging.

    Returns:
        dict: A dictionary containing the validated email credentials. Returns
        an empty dictionary if the file is not found or is invalid.
    """
    path = default_email_credentials_file()
    if not os.path.exists(path):
        chip.logger.warning(f'Email credentials are not available: {path}')
        return {}

    with open(path) as f:
        creds = json.load(f)

    try:
        return validate_creds(creds)
    except fastjsonschema.JsonSchemaException as e:
        chip.logger.error(f'Email credentials failed to validate: {e}')
        return {}


def send(chip, msg_type, step, index):
    """
    Constructs and sends an email notification for a specific job event.

    This function checks if a notification is required for the given event type
    based on the chip's configuration. If so, it assembles an email with a
    subject, HTML body, and relevant attachments (logs or images) and sends
    it via the configured SMTP server.

    Args:
        chip (Chip): The Chip object containing all run data and configuration.
        msg_type (str): The type of event triggering the message (e.g., 'begin',
            'fail', 'summary').
        step (str): The step name associated with the event. Can be None for
            global events.
        index (str): The index associated with the event. Can be None for
            global events.
    """
    chip_step, chip_index = step, index
    if step is None:
        chip_step = Parameter.GLOBAL_KEY
    if index is None:
        chip_index = Parameter.GLOBAL_KEY
    to = chip.get('option', 'scheduler', 'msgcontact', step=chip_step, index=chip_index)
    event = chip.get('option', 'scheduler', 'msgevent', step=chip_step, index=chip_index)

    if not to or not event:
        # nothing to do
        return

    if 'all' not in event and msg_type not in event:
        # nothing to do
        return

    cred = __load_config(chip)

    if not cred:
        return

    jobname = chip.get("option", "jobname")
    flow = chip.get("option", "flow")

    msg = MIMEMultipart()

    if step and index:
        subject = f'SiliconCompiler : {chip.design} | {jobname} | {step} | {index} | {msg_type}'
    else:
        subject = f'SiliconCompiler : {chip.design} | {jobname} | {msg_type}'

    # Setup email header
    msg['Subject'] = subject

    if "from" in cred:
        msg['From'] = cred["from"]
    else:
        msg['From'] = list(to)[0]
    msg['To'] = ", ".join(to)
    msg['X-Entity-Ref-ID'] = uuid.uuid4().hex  # keep emails from getting grouped

    if cred["max_file_size"] > 0:
        if msg_type == "summary":
            # Handle summary message: attach layout image and metrics summary
            layout_img = report_utils._find_summary_image(chip)
            if layout_img and os.path.isfile(layout_img):
                with open(layout_img, 'rb') as img_file:
                    img_attach = MIMEApplication(img_file.read())
                    img_attach.add_header('Content-Disposition',
                                          'attachment',
                                          filename=os.path.basename(layout_img))
                    msg.attach(img_attach)

            runtime = RuntimeFlowgraph(
                chip.get("flowgraph", flow, field='schema'),
                from_steps=chip.get('option', 'from'),
                to_steps=chip.get('option', 'to'),
                prune_nodes=chip.get('option', 'prune'))

            nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
                report_utils._collect_data(chip, flow=flow,
                                           flowgraph_nodes=runtime.get_nodes())

            text_msg = get_file_template('email/summary.j2').render(
                design=chip.design,
                nodes=nodes,
                errors=errors,
                metrics=metrics,
                metrics_unit=metrics_unit,
                metric_keys=metrics_to_show)
        else:
            # Handle general node message: attach log files and node-specific data
            # Attach logs
            for log in (f'sc_{step}_{index}.log', f'{step}.log'):
                log_file = f'{chip.getworkdir(step=step, index=index)}/{log}'
                if os.path.exists(log_file):
                    with sc_open(log_file) as f:
                        file_content = f.read().splitlines()
                        # Limit to max_file_size
                        file_content = file_content[-cred["max_file_size"]:]
                        log_attach = MIMEApplication("\n".join(file_content))
                        log_name, _ = os.path.splitext(log)
                        # Make attachment a txt file to avoid issues with tools not loading .log
                        log_attach.add_header('Content-Disposition',
                                              'attachment',
                                              filename=f'{log_name}.txt')
                        msg.attach(log_attach)

            # Collect records for the specific node
            records = {}
            for record in chip.getkeys('record'):
                value = None
                if chip.get('record', record, field='pernode').is_never():
                    value = chip.get('record', record)
                else:
                    value = chip.get('record', record, step=step, index=index)

                if value is not None:
                    records[record] = value

            # Collect metrics for the specific node
            nodes, errors, metrics, metrics_unit, metrics_to_show, _ = \
                report_utils._collect_data(chip, flow=flow, flowgraph_nodes=[(step, index)])

            status = chip.get('record', 'status', step=step, index=index)

            # Render the general email template
            text_msg = get_file_template('email/general.j2').render(
                design=chip.design,
                job=jobname,
                step=step,
                index=index,
                status=status,
                records=records,
                nodes=nodes,
                errors=errors,
                metrics=metrics,
                metrics_unit=metrics_unit,
                metric_keys=metrics_to_show)

    body = MIMEText(text_msg, 'html')
    msg.attach(body)

    # Determine whether to use SSL for the SMTP connection
    if cred['ssl']:
        smtp_use = smtplib.SMTP_SSL
    else:
        smtp_use = smtplib.SMTP

    # Connect to the SMTP server and send the email
    with smtp_use(cred["server"], cred["port"]) as smtp_server:
        do_send = False
        try:
            smtp_server.login(cred["username"], cred["password"])
            do_send = True
        except smtplib.SMTPAuthenticationError as e:
            chip.logger.error(f'Unable to authenticate to email server: {e}')
        except Exception as e:
            chip.logger.error(f'An error occurred during login to email server: {e}')

        if do_send:
            try:
                smtp_server.sendmail(msg['From'], to, msg.as_string())
            except Exception as e:
                chip.logger.error(f'An error occurred while sending email: {e}')


if __name__ == "__main__":
    # Example usage for testing the send function
    from siliconcompiler import Chip
    from siliconcompiler.targets import freepdk45_demo
    chip = Chip('test')
    chip.use(freepdk45_demo)
    chip.set('option', 'scheduler', 'msgevent', 'ALL')
    # To test, uncomment the following line and fill in a valid email address
    # chip.set('option', 'scheduler', 'msgcontact', 'your.email@example.com')
    send(chip, "BEGIN", "import", "0")
