import pygame

class PopupText:
    def __init__(self, surface, font):
        self.display_surface = surface
        self.popup_images = {}  # Dictionary to store different popup images
        self.messages = []
        self.font = font

    def add_popup_image(self, name, image):
        # Method to register new popup images
        self.popup_images[name] = image

    def add_message(self, text, image_type='status_scroll', duration=2000):
        current_time = pygame.time.get_ticks()

        # Check for duplicates
        for msg in self.messages:
            if msg['text'] == text and current_time - msg['spawn_time'] < 1000:
                return

        # Limit to last 3 messages (or whatever number you prefer)
        if len(self.messages) >= 3:
            self.messages.pop(0)  # Remove oldest message

        self.messages.append({
            'text': text,
            'image_type': image_type,
            'spawn_time': current_time,
            'duration': duration
        })
    
    def update(self):
        if not self.popup_images:
            return
        current_time = pygame.time.get_ticks()

        self.messages = [msg for msg in self.messages 
                        if current_time - msg['spawn_time'] < msg['duration']]
    
    def draw(self):
        
        if not self.popup_images or not self.messages:
            return

        screen_width = self.display_surface.get_width()
        screen_height = self.display_surface.get_height()

        base_y = screen_height - 100
        message_spacing = 80  # Space between each scroll
        line_spacing = 20    # Space between lines within a message

        for i, message in enumerate(reversed(self.messages)):
    
            image_type = message.get('image_type', 'status_scroll')  # Default to 'scroll' if not specified
            if image_type not in self.popup_images:
                continue  # Skip messages with invalid image types

            current_image = self.popup_images[image_type]
            lines = message['text'].split('\n')
            num_lines = len(lines)

            current_y = base_y - (i * (message_spacing + (num_lines - 1) * line_spacing))

            popup_rect = current_image.get_rect(center=(screen_width // 2, current_y))
            self.display_surface.blit(current_image, popup_rect)

            text_start_y = popup_rect.centery - ((num_lines - 1) * line_spacing) // 2

            for j, line in enumerate(lines):
                text_surface = self.font.render(line, True, (0, 0, 0))
                text_rect = text_surface.get_rect(
                    center=(popup_rect.centerx, 
                           text_start_y + (j * line_spacing))
                )
                self.display_surface.blit(text_surface, text_rect)