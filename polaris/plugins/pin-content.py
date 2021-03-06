from re import findall

from firebase_admin import db
from polaris.types import AutosaveDict
from polaris.utils import (delete_data, generate_command_help, get_input,
                           init_if_empty, is_command, set_data,
                           wait_until_received)


class plugin(object):
    # Loads the text strings from the bots language #

    def __init__(self, bot):
        self.bot = bot
        self.commands = self.bot.trans.plugins.pins.commands
        self.description = self.bot.trans.plugins.pins.description
        self.update_triggers()

    # Plugin action #
    def run(self, m):
        input = get_input(m)

        # List all pins #
        if is_command(self, 1, m.content):
            pins = []
            for pin in self.bot.pins:
                if 'creator' in self.bot.pins[pin] and self.bot.pins[pin].creator == m.sender.id:
                    pins.append(pin)

            if len(pins) > 0:
                text = self.bot.trans.plugins.pins.strings.pins % len(pins)
                for pin in pins:
                    text += '\n • #%s' % pin

            else:
                text = self.bot.trans.plugins.pins.strings.no_pins

            # If the message is too long send an error message instead #
            if len(text) <= 4096:
                return self.bot.send_message(m, text, extra={'format': 'HTML'})
            else:
                return self.bot.send_message(m, self.bot.trans.errors.unknown, extra={'format': 'HTML'})

        # Add a pin #
        elif is_command(self, 2, m.content):
            if not input:
                return self.bot.send_message(m, generate_command_help(self, m.content), extra={'format': 'HTML'})
                # return self.bot.send_message(m, self.bot.trans.errors.missing_parameter, extra={'format': 'HTML'})

            if input.startswith('#'):
                input = input.lstrip('#')
            input = input.lower()

            if not m.reply:
                return self.bot.send_message(m, self.bot.trans.errors.needs_reply, extra={'format': 'HTML'})

            if input in self.bot.pins:
                return self.bot.send_message(m, self.bot.trans.plugins.pins.strings.already_pinned % input, extra={'format': 'HTML'})

            if m.reply.type == 'text' and m.reply.content.startswith(self.bot.config.prefix):
                pin_type = 'command'
            else:
                pin_type = m.reply.type

            self.bot.pins[input] = {
                'content': m.reply.content.replace('<', '&lt;').replace('>', '&gt;'),
                'creator': m.sender.id,
                'type': pin_type
            }
            set_data('pins/%s/%s' %
                     (self.bot.name, input), self.bot.pins[input])
            self.update_triggers()

            return self.bot.send_message(m, self.bot.trans.plugins.pins.strings.pinned % input, extra={'format': 'HTML'})

        # Remove a pin #
        elif is_command(self, 3, m.content):
            if not input:
                return self.bot.send_message(m, generate_command_help(self, m.content), extra={'format': 'HTML'})
                # return self.bot.send_message(m, self.bot.trans.errors.missing_parameter, extra={'format': 'HTML'})

            if input.startswith('#'):
                input = input.lstrip('#')
            input = input.lower()

            if not input in self.bot.pins:
                return self.bot.send_message(m, self.bot.trans.plugins.pins.strings.not_found % input, extra={'format': 'HTML'})

            if not m.sender.id == self.bot.pins[input].creator:
                return self.bot.send_message(m, self.bot.trans.plugins.pins.strings.not_creator % input, extra={'format': 'HTML'})

            delete_data('pins/%s/%s' % (self.bot.name, input))
            del self.bot.pins[input]
            self.update_triggers()

            return self.bot.send_message(m, self.bot.trans.plugins.pins.strings.unpinned % input, extra={'format': 'HTML'})

        # Check what pin was triggered #
        else:
            # Finds the first 3 pins of the message and sends them. #
            pins = findall(r"#(\w+)", m.content.lower())
            count = 3

            for pin in pins:
                if pin in self.bot.pins:
                    # You can reply with a pin and the message will reply too. #
                    if m.reply:
                        reply = m.reply.id
                    else:
                        reply = m.id

                    if 'content' in self.bot.pins[pin] and 'type' in self.bot.pins[pin]:
                        if (self.bot.pins[pin].type == 'command'):
                            m.content = self.bot.pins[pin].content
                            self.bot.inbox.put(m)
                            return self.bot.on_message_receive(m)

                        else:
                            self.bot.send_message(m, self.bot.pins[pin].content, self.bot.pins[pin].type, extra={
                                'format': 'HTML'}, reply=reply)

                        count -= 1

                if count == 0:
                    return

    def update_triggers(self):
        # Add new triggers #
        for pin, attributes in self.bot.pins.items():
            if not next((i for i, d in enumerate(self.commands) if 'command' in d and d.command == '#' + pin), None):
                self.commands.append({
                    'command': '#' + pin,
                    'hidden': True
                })

        # Remove unused triggers #
        for command in self.commands:
            if 'hidden' in command and command.hidden and not command.command.lstrip('#') in self.bot.pins:
                self.commands.remove(command)
