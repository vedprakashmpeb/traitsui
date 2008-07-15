#-------------------------------------------------------------------------------
#
#  Copyright (c) 2007, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#
#  Author: David C. Morrill
#  Date:   07/14/2008
#
#-------------------------------------------------------------------------------

""" Traits UI simple, scrubber-based integer or float value editor.
"""

#-------------------------------------------------------------------------------
#  Imports:
#-------------------------------------------------------------------------------

import wx

from math \
   import log10, pow

from enthought.traits.api \
    import Any, Range, Str, Float, Color, TraitError, on_trait_change
    
from enthought.traits.ui.ui_traits \
    import Alignment
    
from enthought.traits.ui.wx.editor \
    import Editor
    
from enthought.traits.ui.wx.basic_editor_factory \
    import BasicEditorFactory
    
from enthought.pyface.timer.api \
    import do_after
    
from constants \
    import ErrorColor
    
from image_slice \
    import paint_parent

#-------------------------------------------------------------------------------
#  '_ScrubberEditor' class:
#-------------------------------------------------------------------------------
                               
class _ScrubberEditor ( Editor ):
    """ Traits UI simple, scrubber-based integer or float value editor.
    """
    
    # The low end of the slider range:
    low = Any
    
    # The high end of the slider range:
    high = Any
    
    # The smallest allowed increment:
    increment = Float

    # The current text being displayed:
    text = Str
    
    #-- Class Variables --------------------------------------------------------
    
    text_styles = {
        'left':   wx.TE_LEFT,
        'center': wx.TE_CENTRE,
        'right':  wx.TE_RIGHT
    }
        
    #---------------------------------------------------------------------------
    #  Finishes initializing the editor by creating the underlying toolkit
    #  widget:
    #---------------------------------------------------------------------------
        
    def init ( self, parent ):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        factory = self.factory
        
        # Establish the range of the slider:
        low_name  = high_name = ''
        low, high = factory.low, factory.high
        if high <= low:
            low = high = None
            range      = self.object.trait( self.name ).handler
            if isinstance( range, Range ):
                low_name, high_name = range._low_name, range._high_name
                
                if low_name == '':
                    low = range._low
                    
                if high_name == '':
                    high = range._high
        
        # Create the control:
        self.control = control = wx.Window( parent, -1,
                                            size  = wx.Size( 50, 18 ),
                                            style = wx.FULL_REPAINT_ON_RESIZE |
                                                    wx.TAB_TRAVERSAL )
                                           
        # Set up the painting event handlers:
        wx.EVT_ERASE_BACKGROUND( control, self._erase_background )
        wx.EVT_PAINT(            control, self._on_paint )
        wx.EVT_SET_FOCUS(        control, self._set_focus )
        
        # Set up mouse event handlers:
        wx.EVT_LEAVE_WINDOW( control, self._leave_window )
        wx.EVT_ENTER_WINDOW( control, self._enter_window )
        wx.EVT_LEFT_DOWN(    control, self._left_down )
        wx.EVT_LEFT_UP(      control, self._left_up )
        wx.EVT_MOTION(       control, self._motion )
        
        # Set up the control resize handler:
        wx.EVT_SIZE( control, self._resize )

        # Set the tooltip:
        self._can_set_tooltip = (not self.set_tooltip())

        # Save the values we calculated:
        self.set( low = low, high = high )
        self.sync_value( low_name,  'low',  'from' )
        self.sync_value( high_name, 'high', 'from' )
        
        # Force a reset (in case low = high = None, which won't cause a
        # notification to fire):
        self._reset_scrubber()
        
    #---------------------------------------------------------------------------
    #  Disposes of the contents of an editor:
    #---------------------------------------------------------------------------
    
    def dispose ( self ):
        """ Disposes of the contents of an editor.
        """
        # Remove all of the wx event handlers:
        control = self.control
        wx.EVT_ERASE_BACKGROUND( control, None )
        wx.EVT_PAINT(            control, None )
        wx.EVT_SET_FOCUS(        control, None )
        wx.EVT_LEAVE_WINDOW(     control, None )
        wx.EVT_ENTER_WINDOW(     control, None )
        wx.EVT_LEFT_DOWN(        control, None )
        wx.EVT_LEFT_UP(          control, None )
        wx.EVT_MOTION(           control, None )
        wx.EVT_SIZE(             control, None )
                        
    #---------------------------------------------------------------------------
    #  Updates the editor when the object trait changes external to the editor:
    #---------------------------------------------------------------------------

    def update_editor ( self ):
        """ Updates the editor when the object trait changes externally to the
            editor.
        """
        self.text       = '%g' % self.value
        self._text_size = None
        self._refresh()
                        
    #---------------------------------------------------------------------------
    #  Updates the object when the scrubber value changes:
    #---------------------------------------------------------------------------
        
    def update_object ( self, value ):
        """ Updates the object when the scrubber value changes.
        """
        if value != self.value:
            try:
                self.value = value
                self.update_editor()
            except TraitError:
                value = int( value )
                if value != self.value:
                    self.value = value
                    self.update_editor()

    #---------------------------------------------------------------------------
    #  Handles an error that occurs while setting the object's trait value:
    #---------------------------------------------------------------------------
 
    def error ( self, excp ):
        """ Handles an error that occurs while setting the object's trait value.
        """
        pass
        
    #-- Private Methods --------------------------------------------------------

    @on_trait_change( 'low, high' )
    def _reset_scrubber ( self ):
        """ Sets the the current tooltip.
        """
        low, high = self.low, self.high
        if self._can_set_tooltip:
            if high is None:
                tooltip = ''
                if low is not None:
                    tooltip = '[%g..]' % low
            elif low is None:
                tooltip = '[..%g]' % high
            else:
                tooltip = '[%g..%g]' % ( low, high )
                
            self.control.SetToolTipString( tooltip )
            
        # Establish the slider increment:
        increment = self.factory.increment
        if increment <= 0.0:
            if (low is None) or (high is None) or isinstance( low, int ):
                increment = 1.0
            else:
                increment = pow( 10, round( log10( (high - low) / 100.0 ) ) )
                
            self.increment = increment
            
        self.update_editor()
            
    def _get_text_bounds ( self ):
        """ Get the window bounds of where the current text should be
            displayed.
        """
        tdx, tdy, descent, leading = self._get_text_size()
        wdx, wdy  = self.control.GetClientSizeTuple()
        ty        = ((wdy - (tdy - descent)) / 2) - 1
        alignment = self.factory.alignment
        if alignment == 'left':
            tx = 4
        elif alignment == 'center':
            tx = (wdx - tdx) / 2
        else:
            tx = wdx - tdx - 4
            
        return ( tx, ty, tdx, tdy )
        
    def _get_text_size ( self ):
        """ Returns the text size information for the window.
        """
        if self._text_size is None:
            self._text_size = self.control.GetFullTextExtent( 
                                               self.text.strip() or 'M' )
            
        return self._text_size
        
    def _refresh ( self ):
        """ Refreshes the contents of the control.
        """
        if self.control is not None:
            self.control.Refresh()
        
    def _set_scrubber_position ( self, event, delta ):
        """ Calculates a new scrubber value for a specified mouse position 
            change.
        """
        clicks    = 3
        increment = self.increment
        if event.ShiftDown():
            increment *= 10.0
            clicks     = 7
        elif event.ControlDown():
            increment /= 10.0
            
        value = self._value + (delta / clicks) * increment
        
        if self.low is not None:
            value = max( value, self.low )
            
        if self.high is not None:
            value = min( value, self.high )
            
        self.update_object( value )
            
    def _delayed_click ( self ):
        """ Handle a delayed click response.
        """
        self._pending = False

    def _pop_up_text ( self ):
        """ Pop-up a text control to allow the user to enter a value using
            the keyboard.
        """
        control = self.control
        control.SetCursor( wx.StockCursor( wx.CURSOR_ARROW ) )
        self._text = text = wx.TextCtrl( control, -1, self.text,
                            size  = control.GetSize(),
                            style = self.text_styles[ self.factory.alignment ] |
                                    wx.TE_PROCESS_ENTER )
        text.SetSelection( -1, -1 )
        text.SetFocus()
        wx.EVT_TEXT_ENTER( control, text.GetId(), self._text_completed )
        wx.EVT_KILL_FOCUS( text, self._text_completed )
        wx.EVT_CHAR( text, self._key_entered )

    def _destroy_text ( self ):
        """ Destroys the current text control.
        """
        self.control.DestroyChildren()
        self.control.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
        self._text = None
        
    #--- wxPython Event Handlers -----------------------------------------------
            
    def _erase_background ( self, event ):
        """ Do not erase the background here (do it in the 'on_paint' handler).
        """
        pass
           
    def _on_paint ( self, event ):
        """ Paint the background using the associated ImageSlice object.
        """
        control  = self.control
        dc       = wx.PaintDC( control )
        factory  = self.factory
        wdx, wdy = control.GetClientSizeTuple()
        
        # Draw the background:
        color = factory.color_
        if self._x is not None:
            if factory.active_color_ is not None:
                color = factory.active_color_
        elif self._hover:
            if factory.hover_color_ is not None:
                color = factory.hover_color_
                
        if color is None:
            paint_parent( dc, control )
            brush = wx.TRANSPARENT_BRUSH
        else:
            brush = wx.Brush( color )
            
            
        color = factory.border_color_
        if color is not None:
            pen = wx.Pen( color )
        else:
            pen = wx.TRANSPARENT_PEN
            
        if (pen != wx.TRANSPARENT_PEN) or (brush != wx.TRANSPARENT_BRUSH):
            dc.SetBrush( brush )
            dc.SetPen( pen )
            dc.DrawRectangle( 0, 0, wdx, wdy )
        
        # Draw the current text value:
        dc.SetBackgroundMode( wx.TRANSPARENT )
        dc.SetTextForeground( factory.text_color_ )
        dc.SetFont( control.GetFont() )
        tx, ty, tdx, tdy = self._get_text_bounds()
        dc.DrawText( self.text, tx, ty )
        
    def _resize ( self, event ):
        """ Handles the control being resized.
        """
        if self._text is not None:
            self._text.SetSize( self.control.GetSize() )
    
    def _set_focus ( self, event ):
        """ Handle the control getting the keyboard focus.
        """
        if (self._x is None) and (self._text is None):
            self._pop_up_text()
            
        event.Skip()
        
    def _enter_window ( self, event ):
        """ Handles the mouse entering the window.
        """
        self._hover = True
        self.control.SetCursor( wx.StockCursor( wx.CURSOR_HAND ) )
        self.control.Refresh()

    def _leave_window ( self, event ):
        """ Handles the mouse leaving the window.
        """
        self._hover = False
        self.control.Refresh()
    
    def _left_down ( self, event ):
        """ Handles the left mouse being pressed.
        """
        self._x, self._y = event.GetX(), event.GetY()
        self._value      = self.value
        self._pending    = True
        self.control.CaptureMouse()
        self.control.SetFocus()
        
        if self.factory.active_color_ != self.factory.hover_color_:
            self.control.Refresh()
            
        do_after( 150, self._delayed_click )
    
    def _left_up ( self, event ):
        """ Handles the left mouse button being released.
        """
        self.control.ReleaseMouse()
        if self._pending:
            self._pop_up_text()
            
        self._x = self._y = self._value = self._pending = None
        
        if self._hover:
            self.control.Refresh()
        
    def _motion ( self, event ):
        """ Handles the mouse moving.
        """
        if self._x is not None:
            x, y = event.GetX(), event.GetY()
            dx   = x - self._x
            adx  = abs( dx )
            dy   = y - self._y
            ady  = abs( dy )
            if self._pending:
                if (adx + ady) < 3:
                    return
                self._pending = False
            
            if adx > ady:
                delta = dx
            else:
                delta = -dy
                
            self._set_scrubber_position( event, delta )
            
    def _update_value ( self, event ):
        """ Updates the object value from the current text control value.
        """
        control = event.GetEventObject()
        try:
            self.update_object( float( control.GetValue() ) )
            
            return True
            
        except TraitError:
            control.SetBackgroundColour( ErrorColor )
            control.Refresh()
            
            return False
            
    def _text_completed ( self, event ):
        """ Handles the user pressing the 'Enter' key in the text control.
        """
        if self._update_value( event ):
            self._destroy_text()
        
    def _key_entered ( self, event ):
        """ Handles individual key strokes while the text control is active.
        """
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            self._destroy_text()
            return
        
        if key_code == wx.WXK_TAB:
            if self._update_value( event ):
                if event.ShiftDown():
                    self.control.Navigate( 0 )
                else:
                    self.control.Navigate()
            return
            
        event.Skip()
                    
#-------------------------------------------------------------------------------
#  Create the editor factory object:
#-------------------------------------------------------------------------------

# wxPython editor factory for themed slider editors:
class ScrubberEditor ( BasicEditorFactory ):
    
    # The editor class to be created:
    klass = _ScrubberEditor
    
    # The low end of the scrubber range:
    low = Float
    
    # The high end of the scrubber range:
    high = Float
    
    # The normal increment (default: auto-calculate):
    increment = Float
    
    # The alignment of the text within the scrubber:
    alignment = Alignment( 'center' )
    
    # The background color for the scrubber:
    color = Color( None )
    
    # The hover mode background color for the scrubber:
    hover_color = Color( None )
    
    # The active mode background color for the scrubber:
    active_color = Color( None )
    
    # The scrubber border color:
    border_color = Color( None )
    
    # The color to use for the value text:
    text_color = Color( 'black' )
                 
