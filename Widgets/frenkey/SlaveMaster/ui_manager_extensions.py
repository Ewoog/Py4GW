from Py4GWCoreLib import UIManager

class UIManagerExtensions:
    @staticmethod
    def IsElementVisible(frame_id: int) -> bool:
        """
        Check if a specific frame is open in the UI.

        Args:
            frame_id (int): The ID of the frame to check.

        Returns:
            bool: True if the frame is open, False otherwise.
        """
        return isinstance(frame_id, int) and frame_id > 0

    @staticmethod
    def IsMerchantWindowOpen() -> bool:
        merchant_window_frame_id = UIManager.GetFrameIDByHash(3613855137)
        # merchant_window_frame_inner_id = UIManager.GetChildFrameID(3613855137, [
        #                                                            0])
        # merchant_window_funds_id = UIManager.GetFrameIDByHash(3068881268)
        # merchant_window_buy_button_id = UIManager.GetFrameIDByHash(1532320307)

        return UIManagerExtensions.IsElementVisible(merchant_window_frame_id)

    @staticmethod
    def IsConfirmMaterialsWindowOpen() -> tuple[bool, int, int]:
        # salvage_lower_kit_id = UIManager.GetChildFrameID(140452905, [6,98])
        salvage_lower_kit_yes_button_id = UIManager.GetChildFrameID(140452905, [
                                                                    6, 98, 6])
        salvage_lower_kit_no_button_id = UIManager.GetChildFrameID(140452905, [
                                                                   6, 98, 4])

        return UIManagerExtensions.IsElementVisible(salvage_lower_kit_yes_button_id), salvage_lower_kit_yes_button_id, salvage_lower_kit_no_button_id

    @staticmethod
    def ConfirmLesserSalvage():
        salvage_lower_kit_yes_button_id = UIManager.GetChildFrameID(140452905, [
                                                                    6, 98, 6])
        UIManager.FrameClick(salvage_lower_kit_yes_button_id)

    @staticmethod
    def IsSalvageWindowOpen() -> bool:
        salvage_window_frame_id = UIManager.GetFrameIDByHash(684387150)
        # salvage_window_salvage_button_id = UIManager.GetChildFrameID(684387150, [2])
        # salvage_window_cancel_button_id = UIManager.GetChildFrameID(684387150, [1])

        return UIManagerExtensions.IsElementVisible(salvage_window_frame_id)